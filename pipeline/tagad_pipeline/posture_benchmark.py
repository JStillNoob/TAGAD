"""Explicit offline-only A5 evaluation; importing this module loads no models."""

import argparse
import json
import math
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import sha256, verify_artifacts
from .configuration import load_configuration
from .posture import PostureMetrics


MODEL_DIR = Path(__file__).resolve().parents[2] / 'backend' / 'model_artifacts'
MANIFEST = Path(__file__).resolve().parents[1] / 'artifact-manifest.json'


def parser():
    result = argparse.ArgumentParser(description='Evaluate A5 posture on local recorded videos only.')
    result.add_argument('--config', type=Path, required=True)
    result.add_argument('--mode', choices=('baseline', 'pose'), default='pose')
    result.add_argument('--pose-model', type=Path)
    result.add_argument('--model-dir', type=Path, default=MODEL_DIR)
    result.add_argument('--output', type=Path, required=True)
    result.add_argument('--analysis-hz', type=float, default=2.5)
    result.add_argument('--source-seconds', type=float, default=60)
    result.add_argument('--joint-confidence', type=float, default=0.5)
    result.add_argument('--target-revision', default='draft-a5-20261105')
    return result


def validate_inputs(args):
    for value in (args.analysis_hz, args.source_seconds):
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Sampling rate and source duration must be finite and positive.')
    if not math.isfinite(args.joint_confidence) or not 0 < args.joint_confidence <= 1:
        raise ValueError('Joint confidence must be between zero and one.')
    if not args.target_revision or len(args.target_revision) > 64 or any(
        not (character.isascii() and (character.isalnum() or character in '-_'))
        for character in args.target_revision
    ):
        raise ValueError('Use an anonymous target revision containing letters, digits, hyphens, or underscores.')
    configuration = load_configuration(args.config)
    if len({source.position for source in configuration.cameras}) != len(configuration.cameras):
        raise ValueError('Use one recorded video per camera position.')
    for source in configuration.cameras:
        if source.source_type != 'simulated' or not Path(source.source).is_file():
            raise ValueError('Every source must be an existing local recorded video.')
    if args.mode == 'pose' and (
        args.pose_model is None or args.pose_model.suffix.lower() != '.pt'
        or not args.pose_model.is_file()
    ):
        raise ValueError('Pose mode requires an existing local .pt checkpoint.')
    if args.output.exists():
        raise ValueError('Choose a new output file to preserve prior measurements.')
    return configuration.cameras


def pose_people(result):
    if result.boxes is None:
        return []
    boxes = result.boxes.xyxy.cpu().tolist()
    keypoints = result.keypoints.data.cpu().tolist() if result.keypoints is not None else []
    return [
        {'box': box, 'keypoints': keypoints[index] if index < len(keypoints) else []}
        for index, box in enumerate(boxes)
    ]


def latency_summary(samples):
    ordered = sorted(samples)
    return {
        'samples': len(ordered),
        'mean_ms': round(1000 * statistics.mean(ordered), 3) if ordered else None,
        'p95_ms': round(1000 * ordered[math.ceil(0.95 * len(ordered)) - 1], 3) if ordered else None,
        'maximum_ms': round(1000 * ordered[-1], 3) if ordered else None,
    }


def recording_timing(source):
    manifest_path = Path(source.source).parent / 'recording-manifest.json'
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    matches = [
        segment for camera in manifest['cameras'] if camera['camera'] == source.position
        for segment in camera.get('segments', []) if segment['file'] == Path(source.source).name
    ]
    if len(matches) != 1:
        raise ValueError('Recording timing metadata must match the input video.')
    timing = {key: matches[0].get(key, 0) for key in (
        'corrected_timestamp_packets', 'tail_estimated_timestamp_packets', 'inferred_dts_packets',
    )}
    if any(type(value) is not int or value < 0 for value in timing.values()):
        raise ValueError('Recording timing counts must be nonnegative integers.')
    adjustment = matches[0].get('max_timestamp_adjustment_seconds', 0.0)
    if not isinstance(adjustment, (int, float)) or not math.isfinite(adjustment) or adjustment < 0:
        raise ValueError('Recording timing adjustment must be finite and nonnegative.')
    return {**timing, 'max_timestamp_adjustment_seconds': adjustment, 'manifest_sha256': sha256(manifest_path)}


def evaluate_camera(source, capture, fps, duration, models, pose_model, lock, start, stop, args):
    import psutil
    import torch

    from .benchmark import add_analysis, new_accumulator, public_metrics
    from .inference import CameraPipeline

    pipeline = CameraPipeline(models)
    posture = PostureMetrics(args.joint_confidence)
    aggregate = new_accumulator()
    latencies, pose_latencies = [], []
    process = psutil.Process()
    rss_peak, device_peak = 0, 0
    skipped = 0
    origin, previous_timestamp = None, None
    source_seconds_read = 0.0
    frame_size = None
    next_sample = 0.0
    status, error = 'completed', None
    start.wait()
    started = time.perf_counter()
    try:
        for video_frame in capture.decode(video=0):
            if stop.is_set():
                break
            if video_frame.pts is None or not video_frame.time_base or video_frame.time_base <= 0:
                raise ValueError('Recorded frame timestamps are unavailable.')
            presentation_time = video_frame.pts * video_frame.time_base
            if origin is None:
                origin = presentation_time
            timestamp = float(presentation_time - origin)
            if previous_timestamp is not None and timestamp <= previous_timestamp:
                raise ValueError('Recorded frame timestamps must increase.')
            previous_timestamp = timestamp
            if timestamp >= duration:
                source_seconds_read = duration
                break
            if video_frame.duration < 0:
                raise ValueError('Recorded frame duration must be nonnegative.')
            source_seconds_read = min(duration, timestamp + float(video_frame.duration * video_frame.time_base))
            frame_size = [video_frame.width, video_frame.height]
            if timestamp + 1e-9 < next_sample:
                skipped += 1
                continue
            next_sample = (math.floor(timestamp * args.analysis_hz + 1e-9) + 1) / args.analysis_hz
            frame = video_frame.to_ndarray(format='bgr24')
            sample_started = time.perf_counter()
            with lock:
                analysis = pipeline.process_frame(frame, timestamp)
                if pose_model is not None:
                    if models.device != 'cpu':
                        torch.cuda.synchronize()
                    pose_started = time.perf_counter()
                    result = pose_model.predict(
                        frame, imgsz=640, conf=0.25, device=models.device,
                        half=False, verbose=False,
                    )[0]
                    people = pose_people(result)
                    if models.device != 'cpu':
                        torch.cuda.synchronize()
                    pose_latencies.append(time.perf_counter() - pose_started)
                if models.device != 'cpu':
                    torch.cuda.synchronize()
            if pose_model is not None:
                tracks = [track for track in pipeline.tracker.tracks.values() if not track.missing]
                posture.update(tracks, people, timestamp, frame.shape[1], frame.shape[0])
            latencies.append(time.perf_counter() - sample_started)
            add_analysis(aggregate, analysis)
            rss_peak = max(rss_peak, process.memory_info().rss)
            if models.device != 'cpu':
                free, total = torch.cuda.mem_get_info()
                device_peak = max(device_peak, total - free)
        else:
            if source_seconds_read + 1e-6 < duration:
                raise ValueError('Recorded video ended before its declared duration.')
    except Exception as failure:
        status, error = 'failed', type(failure).__name__
    finally:
        capture.close()
    elapsed = time.perf_counter() - started
    return {
        'camera': source.position, 'status': status, 'error_type': error,
        'wall_started_at': started, 'wall_ended_at': started + elapsed,
        **public_metrics(aggregate),
        'source_fps': fps, 'source_seconds_read': source_seconds_read,
        'frame_size': frame_size,
        'timestamp_basis': 'decoded presentation timestamps relative to first frame',
        'intentionally_skipped_frames': skipped,
        'wall_seconds': round(elapsed, 3),
        'throughput_hz': round(aggregate['frames'] / elapsed, 3),
        'pipeline_latency': latency_summary(latencies),
        'pose_latency': latency_summary(pose_latencies),
        'posture': posture.summary() if pose_model is not None else None,
        'process_rss_peak_bytes': rss_peak,
        'sampled_total_device_peak_bytes': device_peak if models.device != 'cpu' else None,
    }


def run(args, sources):
    import av
    import torch
    import ultralytics

    from .inference import ModelBundle
    from .worker import model_paths

    captures, models = [], None
    try:
        metadata = []
        for source in sources:
            capture = av.open(source.source)
            captures.append(capture)
            if not capture.streams.video:
                raise ValueError('Recorded video has no video stream.')
            stream = capture.streams.video[0]
            fps = float(stream.average_rate) if stream.average_rate else 0
            source_duration = 0
            if stream.duration is not None and stream.time_base:
                source_duration = float(stream.duration * stream.time_base)
            elif capture.duration is not None:
                source_duration = capture.duration / av.time_base
            if not all(math.isfinite(value) and value > 0 for value in (fps, source_duration)):
                raise ValueError('Recorded video metadata is unavailable.')
            metadata.append((fps, source_duration))
        duration = min(args.source_seconds, *(seconds for _fps, seconds in metadata))
        if duration < 5 or any(args.analysis_hz > fps for fps, _count in metadata):
            raise ValueError('Use at least five seconds of footage and a sampling rate within the source frame rates.')
        manifest = verify_artifacts(args.model_dir, MANIFEST)
        inputs = [
            {'camera': source.position, 'sha256': sha256(source.source), 'recording_timing': recording_timing(source)}
            for source in sources
        ]
        load_started = time.perf_counter()
        models = ModelBundle(**model_paths(args.model_dir))
        pose_model = ultralytics.YOLO(str(args.pose_model.resolve())) if args.mode == 'pose' else None
        if pose_model is not None and pose_model.task != 'pose':
            raise ValueError('The candidate checkpoint must be a pose model.')
        model_load_seconds = time.perf_counter() - load_started
        warmup_started = time.perf_counter()
        warmup_frame = next(captures[0].decode(video=0), None)
        if warmup_frame is None:
            raise ValueError('Warm-up frame is unavailable.')
        frame = warmup_frame.to_ndarray(format='bgr24')
        from .inference import CameraPipeline
        warmup = CameraPipeline(models)
        for index in range(3):
            warmup.process_frame(frame, float(index))
            if pose_model is not None:
                pose_model.predict(
                    frame, imgsz=640, conf=0.25, device=models.device,
                    half=False, verbose=False,
                )
        captures[0].seek(0, stream=captures[0].streams.video[0])
        if models.device != 'cpu':
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
        warmup_seconds = time.perf_counter() - warmup_started
        lock, start, stop = threading.Lock(), threading.Event(), threading.Event()
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            try:
                futures = [
                    executor.submit(evaluate_camera, source, capture, fps, duration, models,
                                    pose_model, lock, start, stop, args)
                    for source, capture, (fps, _seconds) in zip(sources, captures, metadata)
                ]
                start.set()
                results = [future.result() for future in futures]
            except BaseException:
                start.set()
                stop.set()
                raise
        overlap = max(0, min(item['wall_ended_at'] for item in results) - max(
            item['wall_started_at'] for item in results
        ))
        for item in results:
            item.pop('wall_started_at')
            item.pop('wall_ended_at')
        gpu = None
        if models.device != 'cpu':
            _free, capacity = torch.cuda.mem_get_info()
            gpu = {
                'allocated_peak_bytes': torch.cuda.max_memory_allocated(),
                'reserved_peak_bytes': torch.cuda.max_memory_reserved(),
                'sampled_total_device_peak_bytes': max(item['sampled_total_device_peak_bytes'] for item in results),
                'capacity_bytes': capacity,
            }
        payload = {
            'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'mode': args.mode, 'device': str(models.device),
            'pipeline_version': manifest['pipeline_version'],
            'ultralytics_version': ultralytics.__version__, 'torch_version': str(torch.__version__),
            'pose_sha256': sha256(args.pose_model) if pose_model is not None else None,
            'inputs': inputs, 'target_revision': args.target_revision,
            'analysis_hz': args.analysis_hz, 'joint_confidence': args.joint_confidence,
            'temporal_window': {'seconds': 5, 'minimum_samples': 8, 'minimum_span_seconds': 3, 'maximum_gap_seconds': 1},
            'pose_settings': {'image_size': 640, 'person_confidence': 0.25, 'half_precision': False},
            'model_load_seconds': model_load_seconds,
            'source_duration_seconds': duration, 'warmup_seconds': warmup_seconds,
            'common_concurrent_wall_seconds': round(overlap, 6),
            'gpu_memory': gpu, 'cameras': results,
            'combined_student_count': None, 'human_review': 'pending',
            'calibration': 'pending A4 verification', 'feasibility': 'unverified',
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(payload, output, indent=2, allow_nan=False)
        return 0 if all(item['status'] == 'completed' and item['analyzed_frames'] for item in results) else 1
    finally:
        for capture in captures:
            capture.close()
        if models is not None:
            models.close()


def main():
    cli = parser()
    args = cli.parse_args()
    try:
        sources = validate_inputs(args)
        status = run(args, sources)
        print('Offline aggregate report written. Human review pending.')
        return status
    except Exception as error:
        print(f'Offline posture evaluation failed ({type(error).__name__}). Check local inputs and artifacts.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
