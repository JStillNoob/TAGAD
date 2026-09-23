import argparse
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import psutil

from .inference import CameraPipeline, ModelBundle, PipelineConfigurationError
from .worker import DEFAULT_MODEL_DIR, MANIFEST_PATH, model_paths
from .artifacts import verify_artifacts


VIDEO_EXTENSIONS = {'.avi', '.mkv', '.mov', '.mp4', '.webm'}


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def discover_videos(video_dir):
    return sorted(
        path for path in Path(video_dir).iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def new_accumulator():
    return {
        'frames': 0,
        'candidates': 0,
        'valid_faces': 0,
        'confirmed': 0,
        'unclassified': 0,
        'states': Counter(),
        'confidences': [],
    }


def add_analysis(accumulator, analysis):
    accumulator['frames'] += 1
    accumulator['candidates'] += analysis.yolo_candidates
    accumulator['valid_faces'] += analysis.valid_faces
    accumulator['confirmed'] += analysis.confirmed_students
    for prediction in analysis.predictions:
        label = prediction['label']
        if label is None:
            accumulator['unclassified'] += 1
        else:
            accumulator['states'][label] += 1
            accumulator['confidences'].append(float(prediction['confidence']))


def public_metrics(accumulator):
    frames = accumulator['frames']
    classified = sum(accumulator['states'].values())
    confirmed = accumulator['confirmed']
    return {
        'analyzed_frames': frames,
        'mean_candidates': round(accumulator['candidates'] / frames, 3) if frames else 0,
        'mean_valid_faces': round(accumulator['valid_faces'] / frames, 3) if frames else 0,
        'mean_confirmed_students': round(confirmed / frames, 3) if frames else 0,
        'valid_face_rate_percent': round(
            100 * accumulator['valid_faces'] / accumulator['candidates'], 2,
        ) if accumulator['candidates'] else 0,
        'classification_rate_percent': round(
            100 * classified / confirmed, 2,
        ) if confirmed else 0,
        'unclassified_observations': accumulator['unclassified'],
        'average_classification_confidence_percent': round(
            100 * statistics.mean(accumulator['confidences']), 2,
        ) if accumulator['confidences'] else 0,
        'state_observations': dict(sorted(accumulator['states'].items())),
    }


def benchmark_video(path, models, args, angle_number, process):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise PipelineConfigurationError(f'Could not open benchmark video: {path.name}')
    fps = capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not fps or fps <= 0:
        capture.release()
        raise PipelineConfigurationError(f'Video has an invalid frame rate: {path.name}')

    frame_step = max(1, round(fps / args.analysis_hz))
    pipeline = CameraPipeline(
        models,
        yolo_confidence=args.yolo_confidence,
        max_heads=args.max_heads,
        confirmation_seconds=args.confirmation_seconds,
        confirmation_valid_faces=args.minimum_valid_faces,
    )
    total = new_accumulator()
    segments = defaultdict(new_accumulator)
    processing_times = []
    rss_start = process.memory_info().rss
    rss_peak = rss_start
    frame_number = 0
    wall_start = time.perf_counter()

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame_number += 1
            if frame_number % frame_step:
                continue
            source_second = frame_number / fps
            started = time.perf_counter()
            analysis = pipeline.process_frame(frame, source_second)
            processing_times.append(time.perf_counter() - started)
            add_analysis(total, analysis)
            add_analysis(segments[int(source_second // 5) * 5], analysis)
            rss_peak = max(rss_peak, process.memory_info().rss)
    finally:
        capture.release()

    wall_seconds = time.perf_counter() - wall_start
    if not processing_times:
        raise PipelineConfigurationError(f'Video contained no analyzable frames: {path.name}')
    duration_seconds = total_frames / fps
    metrics = public_metrics(total)
    metrics.update({
        'angle': f'angle_{angle_number}',
        'file': path.name,
        'bytes': path.stat().st_size,
        'width': width,
        'height': height,
        'source_fps': round(fps, 3),
        'source_frames': total_frames,
        'source_duration_seconds': round(duration_seconds, 3),
        'requested_analysis_hz': args.analysis_hz,
        'sampled_source_hz': round(metrics['analyzed_frames'] / duration_seconds, 3),
        'wall_seconds': round(wall_seconds, 3),
        'processing_throughput_hz': round(
            metrics['analyzed_frames'] / wall_seconds, 3,
        ) if wall_seconds else 0,
        'realtime_factor': round(duration_seconds / wall_seconds, 3) if wall_seconds else 0,
        'mean_processing_ms': round(1000 * statistics.mean(processing_times), 2),
        'p95_processing_ms': round(1000 * percentile(processing_times, 0.95), 2),
        'maximum_processing_ms': round(1000 * max(processing_times), 2),
        'rss_start_mb': round(rss_start / 1024 / 1024, 2),
        'rss_peak_mb': round(rss_peak / 1024 / 1024, 2),
        'rss_growth_mb': round((process.memory_info().rss - rss_start) / 1024 / 1024, 2),
        'segments': [
            {'start_second': second, **public_metrics(accumulator)}
            for second, accumulator in sorted(segments.items())
        ],
    })
    return metrics


def parser():
    result = argparse.ArgumentParser(description='Benchmark TAGAD videos independently.')
    result.add_argument('--video-dir', type=Path, default=Path('pipeline/test_video'))
    result.add_argument(
        '--output', type=Path,
        default=Path('pipeline/benchmark_results/three_angle_benchmark.json'),
    )
    result.add_argument('--model-dir', type=Path, default=DEFAULT_MODEL_DIR)
    result.add_argument('--analysis-hz', type=float, default=8.0)
    result.add_argument('--yolo-confidence', type=float, default=0.60)
    result.add_argument('--confirmation-seconds', type=float, default=1.2)
    result.add_argument('--minimum-valid-faces', type=int, default=5)
    result.add_argument('--max-heads', type=int, default=40)
    return result


def main():
    cli_parser = parser()
    args = cli_parser.parse_args()
    if not args.video_dir.is_dir():
        cli_parser.error(f'Video directory does not exist: {args.video_dir}')
    if args.analysis_hz <= 0:
        cli_parser.error('--analysis-hz must be greater than zero.')
    if not 0 < args.yolo_confidence <= 1:
        cli_parser.error('--yolo-confidence must be between 0 and 1.')
    videos = discover_videos(args.video_dir)
    if not videos:
        raise SystemExit(f'No benchmark videos found in {args.video_dir}.')

    manifest = verify_artifacts(args.model_dir, MANIFEST_PATH)
    models = ModelBundle(**model_paths(args.model_dir))
    process = psutil.Process()
    try:
        results = [
            benchmark_video(path, models, args, index, process)
            for index, path in enumerate(videos, start=1)
        ]
    finally:
        models.close()

    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'pipeline_version': manifest['pipeline_version'],
        'device': str(models.device),
        'configuration': {
            'analysis_hz': args.analysis_hz,
            'yolo_confidence': args.yolo_confidence,
            'confirmation_seconds': args.confirmation_seconds,
            'minimum_valid_faces': args.minimum_valid_faces,
            'max_heads': args.max_heads,
        },
        'results_are_independent': True,
        'combined_student_count': None,
        'videos': results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    for result in results:
        print(
            f"{result['file']}: {result['analyzed_frames']} frames, "
            f"{result['processing_throughput_hz']} analyses/s, "
            f"{result['mean_confirmed_students']} mean confirmed, "
            f"{result['classification_rate_percent']}% classified",
            flush=True,
        )
    print(f'Wrote aggregate-only benchmark to {args.output}', flush=True)


if __name__ == '__main__':
    main()
