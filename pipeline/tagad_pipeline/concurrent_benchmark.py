import argparse
import json
import statistics
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import psutil

from .artifacts import verify_artifacts
from .benchmark import add_analysis, new_accumulator, percentile, public_metrics
from .configuration import load_configuration
from .inference import CameraPipeline, ModelBundle, PipelineConfigurationError
from .worker import DEFAULT_MODEL_DIR, MANIFEST_PATH, model_paths


def run_camera(source, models, model_lock, analysis_hz, deadline, result):
    capture = cv2.VideoCapture(source.source)
    if not capture.isOpened():
        result.update({'status': 'offline', 'error': 'source_unavailable'})
        capture.release()
        return
    pipeline = CameraPipeline(models)
    fps = capture.get(cv2.CAP_PROP_FPS) or analysis_hz
    frame_step = max(1, round(fps / analysis_hz))
    frame_number = 0
    accumulator = new_accumulator()
    latencies = []
    try:
        while time.monotonic() < deadline:
            ok, frame = capture.read()
            if not ok:
                if source.loop and capture.set(cv2.CAP_PROP_POS_FRAMES, 0):
                    frame_number = 0
                    continue
                break
            frame_number += 1
            if frame_number % frame_step:
                continue
            started = time.perf_counter()
            with model_lock:
                analysis = pipeline.process_frame(frame, time.monotonic())
            latencies.append(time.perf_counter() - started)
            add_analysis(accumulator, analysis)
    except Exception as error:
        result.update({'status': 'failed', 'error': type(error).__name__})
    finally:
        capture.release()
    elapsed = max(0.001, result['wall_started_at'] and time.monotonic() - result['wall_started_at'])
    result.update(public_metrics(accumulator))
    result.update({
        'status': result.get('status', 'completed'),
        'throughput_hz': round(accumulator['frames'] / elapsed, 3),
        'mean_latency_ms': round(1000 * statistics.mean(latencies), 2) if latencies else 0,
        'p95_latency_ms': round(1000 * percentile(latencies, 0.95), 2),
        'maximum_latency_ms': round(1000 * max(latencies), 2) if latencies else 0,
    })


def parser():
    result = argparse.ArgumentParser(description='Run the three TAGAD camera sources concurrently.')
    result.add_argument(
        '--config', type=Path,
        default=Path('pipeline/camera_sources.local.json'),
    )
    result.add_argument(
        '--output', type=Path,
        default=Path('pipeline/benchmark_results/concurrent_camera_benchmark.json'),
    )
    result.add_argument('--model-dir', type=Path, default=DEFAULT_MODEL_DIR)
    result.add_argument('--duration-seconds', type=float, default=30)
    return result


def main():
    args = parser().parse_args()
    if args.duration_seconds <= 0:
        raise SystemExit('--duration-seconds must be greater than zero.')
    configuration = load_configuration(args.config)
    sources = [item for item in configuration.cameras if item.source_type == 'simulated']
    if not sources:
        raise SystemExit('No simulated cameras are configured.')
    if any(not item.available for item in sources):
        missing = ', '.join(item.position for item in sources if not item.available)
        raise SystemExit(f'Configured source is unavailable for: {missing}.')

    manifest = verify_artifacts(args.model_dir, MANIFEST_PATH)
    process = psutil.Process()
    rss_before_models = process.memory_info().rss
    models = ModelBundle(**model_paths(args.model_dir))
    rss_after_models = process.memory_info().rss
    model_lock = threading.Lock()
    wall_started_at = time.monotonic()
    deadline = wall_started_at + args.duration_seconds
    results = {
        source.position: {'position': source.position, 'wall_started_at': wall_started_at}
        for source in sources
    }
    threads = [
        threading.Thread(
            target=run_camera,
            args=(
                source, models, model_lock, configuration.analysis_hz,
                deadline, results[source.position],
            ),
            name=f'benchmark-{source.position}',
        )
        for source in sources
    ]
    rss_samples = []
    cpu_samples = []
    process.cpu_percent(None)
    try:
        for thread in threads:
            thread.start()
        while any(thread.is_alive() for thread in threads):
            rss_samples.append(process.memory_info().rss)
            cpu_samples.append(process.cpu_percent(None))
            time.sleep(0.5)
        for thread in threads:
            thread.join()
    finally:
        models.close()

    for result in results.values():
        result.pop('wall_started_at', None)
    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'pipeline_version': manifest['pipeline_version'],
        'device': str(models.device),
        'simulated_sources': True,
        'duration_seconds': args.duration_seconds,
        'shared_model_bundle': True,
        'independent_camera_pipelines': True,
        'results_are_independent': True,
        'combined_student_count': None,
        'model_load_memory_mb': round((rss_after_models - rss_before_models) / 1024 / 1024, 2),
        'rss_peak_mb': round(max(rss_samples, default=rss_after_models) / 1024 / 1024, 2),
        'rss_end_mb': round(process.memory_info().rss / 1024 / 1024, 2),
        'mean_process_cpu_percent': round(statistics.mean(cpu_samples), 2) if cpu_samples else 0,
        'cameras': [results[source.position] for source in sources],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    for result in payload['cameras']:
        print(
            f"{result['position']}: {result.get('analyzed_frames', 0)} analyses, "
            f"{result.get('throughput_hz', 0)} analyses/s, {result['status']}",
            flush=True,
        )
    print(f'Wrote aggregate-only concurrent benchmark to {args.output}', flush=True)


if __name__ == '__main__':
    main()
