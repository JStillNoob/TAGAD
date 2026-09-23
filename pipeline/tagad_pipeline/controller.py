import argparse
import os
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import cv2

from .artifacts import ArtifactVerificationError, verify_artifacts
from .backend_client import BackendClient, BackendRequestError, build_payload
from .configuration import CameraConfigurationError, load_configuration
from .constants import FINAL_LABELS
from .inference import CameraPipeline, ModelBundle, PipelineConfigurationError
from .worker import DEFAULT_MODEL_DIR, MANIFEST_PATH, PIPELINE_VERSION, model_paths, source_value


CONTROLLER_VERSION = f'{PIPELINE_VERSION}-orchestrator-1'
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'camera_sources.local.json'


def diagnostic_counts(predictions):
    values = Counter(
        str(item['label']).strip().lower()
        for item in predictions
        if item.get('label') is not None
    )
    return {label.lower(): values[label.lower()] for label in FINAL_LABELS}


class CameraWorker:
    def __init__(
        self,
        *,
        work,
        source,
        client,
        models,
        inference_lock,
        configuration,
        pipeline_factory=CameraPipeline,
        capture_factory=cv2.VideoCapture,
        clock=time.monotonic,
    ):
        self.work = work
        self.source = source
        self.client = client
        self.models = models
        self.inference_lock = inference_lock
        self.configuration = configuration
        self.pipeline_factory = pipeline_factory
        self.capture_factory = capture_factory
        self.clock = clock
        self.stop_event = threading.Event()
        self.stop_reason = 'shutdown'
        self.thread = threading.Thread(
            target=self._run_guarded,
            name=f'camera-{work["session_id"]}-{work["camera_id"]}',
        )
        self._work_lock = threading.Lock()
        self.registered = False

    @property
    def key(self):
        return self.work['session_id'], self.work['camera_id']

    def start(self):
        self.thread.start()

    def is_alive(self):
        return self.thread.is_alive()

    def update_work(self, work):
        with self._work_lock:
            self.work = work

    def stop(self, reason='shutdown'):
        self.stop_reason = reason
        self.stop_event.set()

    def join(self, timeout=None):
        self.thread.join(timeout)

    def _snapshot(self):
        with self._work_lock:
            return dict(self.work)

    def _heartbeat(self, state, reason='', analysis=None, analysis_rate=0):
        work = self._snapshot()
        predictions = analysis.predictions if analysis else []
        counts = diagnostic_counts(predictions)
        try:
            self.client.heartbeat({
                'session_id': work['session_id'],
                'camera_id': work['camera_id'],
                'state': state,
                'source_type': self.source.source_type,
                'reason': reason,
                'pipeline_version': CONTROLLER_VERSION,
                'analysis_rate': round(analysis_rate, 2),
                'yolo_candidates': analysis.yolo_candidates if analysis else 0,
                'valid_faces': analysis.valid_faces if analysis else 0,
                'confirmed_students': analysis.confirmed_students if analysis else 0,
                'unclassified_students': sum(
                    1 for item in predictions if item.get('label') is None
                ),
                'counts': counts,
            })
        except BackendRequestError:
            # A temporary backend outage must not terminate camera processing.
            return False
        if state == 'starting':
            self.registered = True
        return True

    def _run_guarded(self):
        try:
            self.run()
        except Exception as error:
            if not self.registered:
                self._heartbeat('starting')
            self._heartbeat('offline', 'retry_exhausted')
            print(
                f'Camera worker {self.key[1]} stopped after {type(error).__name__}.',
                file=sys.stderr,
                flush=True,
            )

    def run(self):
        self._heartbeat('starting')
        pipeline = self.pipeline_factory(self.models)
        capture = None
        failures = 0
        injected_disconnect = False
        latest = None
        analyzed = 0
        analysis_started = self.clock()
        next_heartbeat = 0.0
        next_summary = 0.0

        try:
            while not self.stop_event.is_set():
                capture = self.capture_factory(source_value(self.source.source))
                if not capture.isOpened():
                    capture.release()
                    capture = None
                    failures += 1
                    state = (
                        'offline'
                        if failures >= self.configuration.reconnect_attempts
                        else 'reconnecting'
                    )
                    reason = (
                        'source_unavailable'
                        if failures >= self.configuration.reconnect_attempts
                        else 'read_failed'
                    )
                    if not self.registered:
                        self._heartbeat('starting')
                    self._heartbeat(state, reason, latest)
                    self.stop_event.wait(
                        self.configuration.reconnect_backoff_seconds
                        * min(failures, self.configuration.reconnect_attempts)
                    )
                    continue

                if not self.registered:
                    self._heartbeat('starting')
                self._heartbeat('online', 'processing', latest)
                fps = capture.get(cv2.CAP_PROP_FPS) or self.configuration.analysis_hz
                frame_step = max(1, round(fps / self.configuration.analysis_hz))
                frame_number = 0
                processed_this_open = False

                while not self.stop_event.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        if self.source.source_type == 'simulated' and self.source.loop:
                            if capture.set(cv2.CAP_PROP_POS_FRAMES, 0):
                                frame_number = 0
                                continue
                        failures = 0 if processed_this_open else failures + 1
                        state = (
                            'offline'
                            if failures >= self.configuration.reconnect_attempts
                            else 'reconnecting'
                        )
                        self._heartbeat(state, 'read_failed', latest)
                        break

                    frame_number += 1
                    if (
                        self.source.simulate_disconnect_after_frames
                        and not injected_disconnect
                        and frame_number >= self.source.simulate_disconnect_after_frames
                    ):
                        injected_disconnect = True
                        self._heartbeat('reconnecting', 'read_failed', latest)
                        self.stop_event.wait(self.source.simulate_disconnect_seconds)
                        break
                    if frame_number % frame_step:
                        continue

                    timestamp = self.clock()
                    with self.inference_lock:
                        latest = pipeline.process_frame(frame, timestamp)
                    processed_this_open = True
                    failures = 0
                    analyzed += 1
                    elapsed = max(0.001, timestamp - analysis_started)
                    analysis_rate = analyzed / elapsed

                    if timestamp >= next_heartbeat:
                        self._heartbeat('online', 'processing', latest, analysis_rate)
                        next_heartbeat = timestamp + self.configuration.heartbeat_seconds

                    work = self._snapshot()
                    if (
                        work.get('official_analytics')
                        and work.get('slide_event_id')
                        and latest.predictions
                        and timestamp >= next_summary
                    ):
                        payload = build_payload(
                            session_id=work['session_id'],
                            slide_event_id=work['slide_event_id'],
                            camera_id=work['camera_id'],
                            predictions=latest.predictions,
                            pipeline_version=CONTROLLER_VERSION,
                        )
                        try:
                            self.client.submit(payload)
                        except BackendRequestError:
                            pass
                        next_summary = timestamp + self.configuration.summary_seconds

                capture.release()
                capture = None
                if not self.stop_event.is_set():
                    self.stop_event.wait(self.configuration.reconnect_backoff_seconds)
        finally:
            if capture is not None:
                capture.release()
            self._heartbeat('stopped', self.stop_reason, latest)


class CameraController:
    def __init__(
        self,
        *,
        client,
        models,
        configuration,
        worker_factory=CameraWorker,
    ):
        self.client = client
        self.models = models
        self.configuration = configuration
        self.worker_factory = worker_factory
        self.inference_lock = threading.Lock()
        self.workers = {}

    def reconcile(self, sessions):
        desired = {}
        for session in sessions:
            for camera in session.get('cameras', []):
                source = self.configuration.source_for(camera.get('position'))
                if source is None:
                    continue
                key = session['session_id'], camera['camera_id']
                desired[key] = {
                    'session_id': session['session_id'],
                    'slide_event_id': session.get('slide_event_id'),
                    **camera,
                }, source

        for key, worker in list(self.workers.items()):
            if key not in desired:
                worker.stop('session_ended')
                worker.join(self.configuration.poll_seconds)
                del self.workers[key]
            elif not worker.is_alive():
                worker.join()
                del self.workers[key]

        for key, (work, source) in desired.items():
            worker = self.workers.get(key)
            if worker:
                worker.update_work(work)
                continue
            worker = self.worker_factory(
                work=work,
                source=source,
                client=self.client,
                models=self.models,
                inference_lock=self.inference_lock,
                configuration=self.configuration,
            )
            self.workers[key] = worker
            worker.start()

    def run(self, stop_event=None):
        stop_event = stop_event or threading.Event()
        try:
            while not stop_event.is_set():
                try:
                    response = self.client.work()
                    self.reconcile(response.get('sessions', []))
                except BackendRequestError as error:
                    print(
                        f'Controller could not refresh work: {type(error).__name__}.',
                        file=sys.stderr,
                        flush=True,
                    )
                stop_event.wait(self.configuration.poll_seconds)
        finally:
            self.shutdown()

    def shutdown(self):
        for worker in self.workers.values():
            worker.stop('shutdown')
        for worker in self.workers.values():
            worker.join()
        self.workers.clear()


def parser():
    result = argparse.ArgumentParser(description='Run TAGAD offline camera orchestration.')
    result.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    result.add_argument('--model-dir', type=Path, default=DEFAULT_MODEL_DIR)
    result.add_argument('--backend-url', default='http://127.0.0.1:8000')
    return result


def main():
    args = parser().parse_args()
    api_key = os.environ.get('TAGAD_PIPELINE_API_KEY', '')
    if not api_key:
        print(
            'Controller error: set TAGAD_PIPELINE_API_KEY to the backend PIPELINE_API_KEY.',
            file=sys.stderr,
        )
        return 1
    models = None
    try:
        configuration = load_configuration(args.config)
        verify_artifacts(args.model_dir, MANIFEST_PATH)
        models = ModelBundle(**model_paths(args.model_dir))
        CameraController(
            client=BackendClient(args.backend_url, api_key),
            models=models,
            configuration=configuration,
        ).run()
    except KeyboardInterrupt:
        return 0
    except (
        ArtifactVerificationError, BackendRequestError, CameraConfigurationError,
        PipelineConfigurationError, OSError, ValueError,
    ) as error:
        print(f'Controller error: {error}', file=sys.stderr)
        return 1
    finally:
        if models is not None:
            models.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
