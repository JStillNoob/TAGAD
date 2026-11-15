import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from tagad_pipeline.configuration import CameraSource, ControllerConfiguration
from tagad_pipeline.backend_client import BackendRequestError
from tagad_pipeline.controller import CameraController, CameraWorker, StopFileSignal, open_capture


ZERO_COUNTS = {
    'engaged': 0, 'attentive': 0, 'confused': 0, 'bored': 0, 'disengaged': 0,
}


class FakeControllerWorker:
    instances = []

    def __init__(self, **kwargs):
        self.work = kwargs['work']
        self.source = kwargs['source']
        self.alive = True
        self.started = False
        self.stopped_with = None
        self.updates = []
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def is_alive(self):
        return self.alive

    def update_work(self, work):
        self.work = work
        self.updates.append(work)

    def stop(self, reason='shutdown'):
        self.stopped_with = reason
        self.alive = False

    def join(self, timeout=None):
        return None


class ControllerLifecycleTests(unittest.TestCase):
    @patch('tagad_pipeline.controller.cv2.VideoCapture')
    def test_rtsp_connections_have_bounded_open_and_read_timeouts(self, capture):
        import cv2
        open_capture('rtsp://camera.invalid/stream1')
        capture.assert_called_once_with('rtsp://camera.invalid/stream1', cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000,
        ])
        capture.reset_mock()
        open_capture(0)
        capture.assert_called_once_with(0)

    def setUp(self):
        FakeControllerWorker.instances = []
        self.configuration = ControllerConfiguration(cameras=(
            CameraSource('front', 'front.mp4', 'simulated', True, True),
            CameraSource('left', 'left.mp4', 'simulated', True, True),
            CameraSource('right', 'right.mp4', 'simulated', True, True),
        ))
        self.controller = CameraController(
            client=object(), models=object(), configuration=self.configuration,
            worker_factory=FakeControllerWorker,
        )
        self.session = {
            'session_id': 4,
            'slide_event_id': 10,
            'cameras': [
                {'camera_id': 1, 'position': 'front', 'official_analytics': True},
                {'camera_id': 2, 'position': 'left', 'official_analytics': True},
                {'camera_id': 3, 'position': 'right', 'official_analytics': True},
            ],
        }

    def test_starts_one_worker_per_camera_without_duplicates_and_updates_slide(self):
        self.controller.reconcile([self.session])
        self.controller.reconcile([{**self.session, 'slide_event_id': 11}])

        self.assertEqual(len(FakeControllerWorker.instances), 3)
        self.assertEqual(len(self.controller.workers), 3)
        self.assertTrue(all(worker.started for worker in self.controller.workers.values()))
        self.assertTrue(all(worker.work['slide_event_id'] == 11 for worker in self.controller.workers.values()))

    def test_failed_camera_is_replaced_without_stopping_other_cameras(self):
        self.controller.reconcile([self.session])
        failed = self.controller.workers[(4, 2)]
        healthy = self.controller.workers[(4, 1)]
        failed.alive = False

        self.controller.reconcile([self.session])

        self.assertIs(self.controller.workers[(4, 1)], healthy)
        self.assertIsNot(self.controller.workers[(4, 2)], failed)
        self.assertIsNone(healthy.stopped_with)

    def test_prepared_cameras_keep_the_same_workers_when_teaching_starts(self):
        self.controller.reconcile([{**self.session, 'slide_event_id': None}])
        prepared_workers = dict(self.controller.workers)

        self.controller.reconcile([self.session])

        self.assertEqual(len(FakeControllerWorker.instances), 3)
        for key, worker in prepared_workers.items():
            self.assertIs(self.controller.workers[key], worker)
            self.assertIsNone(worker.stopped_with)
            self.assertEqual(worker.work['slide_event_id'], 10)

    def test_removed_session_stops_all_its_workers(self):
        self.controller.reconcile([self.session])
        workers = list(self.controller.workers.values())

        self.controller.reconcile([])

        self.assertFalse(self.controller.workers)
        self.assertTrue(all(worker.stopped_with == 'session_ended' for worker in workers))

    def test_continuation_waits_for_previous_camera_worker_to_exit(self):
        self.controller.reconcile([self.session])
        previous = self.controller.workers[(4, 1)]

        def slow_stop(reason):
            previous.stopped_with = reason

        previous.stop = slow_stop
        continuation = {**self.session, 'session_id': 5, 'slide_event_id': None}
        self.controller.reconcile([continuation])

        self.assertIn((4, 1), self.controller.workers)
        self.assertNotIn((5, 1), self.controller.workers)
        self.assertEqual(previous.stopped_with, 'session_ended')
        previous.alive = False
        self.controller.reconcile([continuation])
        self.assertNotIn((4, 1), self.controller.workers)
        self.assertTrue(self.controller.workers[(5, 1)].started)

    def test_stop_file_signal_stops_controller_loop(self):
        with TemporaryDirectory() as directory:
            stop_path = Path(directory) / 'controller.stop'
            signal = StopFileSignal(stop_path, poll_seconds=0.001)

            self.assertFalse(signal.wait(0.002))
            stop_path.touch()

            self.assertTrue(signal.is_set())
            self.assertTrue(signal.wait(0.002))


class FailedCapture:
    def isOpened(self):
        return False

    def release(self):
        return None


class FrameCapture:
    def __init__(self):
        self.frames = [object()]

    def isOpened(self):
        return True

    def get(self, _property):
        return 8

    def read(self):
        return (True, self.frames.pop()) if self.frames else (False, None)

    def set(self, _property, _value):
        return False

    def release(self):
        return None


class FakePipeline:
    def __init__(self, _models):
        self.reset_count = 0

    def process_frame(self, _frame, _timestamp):
        return SimpleNamespace(
            predictions=[{'label': 'Engaged', 'confidence': 0.9, 'track_id': 1}],
            yolo_candidates=1,
            valid_faces=1,
            confirmed_students=1,
        )

    def diagnostics_snapshot(self):
        return {'schema_version': 1}

    def reset_diagnostics(self):
        self.reset_count += 1


class FakeBackendClient:
    def __init__(self):
        self.heartbeats = []
        self.submissions = []
        self.worker = None

    def heartbeat(self, payload):
        self.heartbeats.append(payload)
        if payload['state'] == 'online' and payload['confirmed_students']:
            self.worker.stop('shutdown')
        return payload

    def submit(self, payload):
        self.submissions.append(payload)
        return payload


class StopOnOfflineClient(FakeBackendClient):
    def heartbeat(self, payload):
        self.heartbeats.append(payload)
        if payload['state'] == 'offline':
            self.worker.stop('shutdown')
        return payload

class WorkerRecoveryTests(unittest.TestCase):
    def test_online_waits_for_the_first_processed_frame(self):
        client = FakeBackendClient()
        pipeline = FakePipeline(object())
        process = pipeline.process_frame

        def first_frame(frame, timestamp):
            self.assertNotIn('online', [item['state'] for item in client.heartbeats])
            return process(frame, timestamp)

        pipeline.process_frame = first_frame
        worker = CameraWorker(
            work={'session_id': 4, 'camera_id': 1, 'position': 'front', 'slide_event_id': None},
            source=CameraSource('front', 'fixture.mp4', 'simulated', False, True),
            client=client, models=object(), inference_lock=threading.Lock(),
            configuration=ControllerConfiguration(cameras=()),
            pipeline_factory=lambda _models: pipeline,
            capture_factory=lambda _source: FrameCapture(),
        )
        client.worker = worker

        worker.run()

        self.assertEqual([item['state'] for item in client.heartbeats], ['starting', 'online', 'stopped'])
        self.assertFalse(client.submissions)

    def test_preparation_produces_readiness_without_engagement_submission(self):
        client = FakeBackendClient()
        worker = CameraWorker(
            work={'session_id': 4, 'camera_id': 1, 'position': 'front', 'slide_event_id': None, 'official_analytics': True},
            source=CameraSource('front', 'fixture.mp4', 'simulated', False, True),
            client=client, models=object(), inference_lock=threading.Lock(),
            configuration=ControllerConfiguration(cameras=()), pipeline_factory=FakePipeline,
            capture_factory=lambda _source: FrameCapture(),
        )
        client.worker = worker
        worker.run()
        self.assertTrue(any(item['state'] == 'online' and item['confirmed_students'] for item in client.heartbeats))
        self.assertFalse(client.submissions)

    def test_stop_during_blocking_read_does_not_analyze_the_returned_frame(self):
        client = FakeBackendClient()
        capture = FrameCapture()
        pipeline = FakePipeline(object())
        worker = CameraWorker(
            work={'session_id': 4, 'camera_id': 1, 'position': 'front', 'slide_event_id': 10},
            source=CameraSource('front', 'private.mp4', 'live', False, True),
            client=client, models=object(), inference_lock=threading.Lock(),
            configuration=ControllerConfiguration(cameras=()),
            pipeline_factory=lambda _models: pipeline, capture_factory=lambda _source: capture,
        )

        def ending_read():
            worker.stop('session_ended')
            return True, object()

        capture.read = ending_read
        client.worker = worker
        with patch.object(pipeline, 'process_frame', wraps=pipeline.process_frame) as process:
            worker.run()
        process.assert_not_called()
        self.assertFalse(client.submissions)
        self.assertEqual(client.heartbeats[-1]['reason'], 'session_ended')
        worker.stop('shutdown')
        self.assertEqual(worker.stop_reason, 'session_ended')

    def test_open_failure_recovers_and_only_official_camera_submits(self):
        captures = iter((FailedCapture(), FrameCapture()))
        client = FakeBackendClient()
        configuration = ControllerConfiguration(
            cameras=(), poll_seconds=0.01, heartbeat_seconds=0.01,
            summary_seconds=0.01, analysis_hz=8, reconnect_attempts=2,
            reconnect_backoff_seconds=0.01,
        )
        worker = CameraWorker(
            work={
                'session_id': 4, 'camera_id': 1, 'position': 'front',
                'slide_event_id': 10, 'official_analytics': True,
            },
            source=CameraSource('front', 'private.mp4', 'live', False, True),
            client=client,
            models=object(),
            inference_lock=threading.Lock(),
            configuration=configuration,
            pipeline_factory=FakePipeline,
            capture_factory=lambda _source: next(captures),
        )
        client.worker = worker

        worker.start()
        worker.join(1)

        self.assertFalse(worker.is_alive())
        states = [item['state'] for item in client.heartbeats]
        self.assertEqual(states[0], 'starting')
        self.assertIn('reconnecting', states)
        self.assertIn('online', states)
        self.assertEqual(states[-1], 'stopped')
        self.assertEqual(len(client.submissions), 1)
        self.assertEqual(client.submissions[0]['camera_id'], 1)
        self.assertEqual(client.submissions[0]['schema_version'], 2)

    def test_configured_disconnect_transitions_to_reconnecting_then_recovers(self):
        client = FakeBackendClient()
        configuration = ControllerConfiguration(
            cameras=(), poll_seconds=0.01, heartbeat_seconds=0.01,
            summary_seconds=0.01, analysis_hz=8, reconnect_attempts=2,
            reconnect_backoff_seconds=0.01,
        )
        opened = []

        def capture_factory(_source):
            opened.append(True)
            return FrameCapture()

        worker = CameraWorker(
            work={
                'session_id': 4, 'camera_id': 1, 'position': 'front',
                'slide_event_id': 10, 'official_analytics': True,
            },
            source=CameraSource(
                'front', 'private.mp4', 'simulated', False, True,
                simulate_disconnect_after_frames=1,
                simulate_disconnect_seconds=0,
            ),
            client=client,
            models=object(),
            inference_lock=threading.Lock(),
            configuration=configuration,
            pipeline_factory=FakePipeline,
            capture_factory=capture_factory,
        )
        client.worker = worker

        worker.start()
        worker.join(1)

        states = [item['state'] for item in client.heartbeats]
        self.assertGreaterEqual(len(opened), 2)
        self.assertIn('reconnecting', states)
        self.assertIn('online', states[states.index('reconnecting') + 1:])
        self.assertEqual(states[-1], 'stopped')

    def test_retry_exhaustion_marks_only_that_worker_offline(self):
        client = StopOnOfflineClient()
        configuration = ControllerConfiguration(
            cameras=(), poll_seconds=0.01, heartbeat_seconds=0.01,
            summary_seconds=0.01, analysis_hz=8, reconnect_attempts=2,
            reconnect_backoff_seconds=0.01,
        )
        worker = CameraWorker(
            work={
                'session_id': 4, 'camera_id': 2, 'position': 'left',
                'slide_event_id': 10, 'official_analytics': False,
            },
            source=CameraSource('left', 'missing.mp4', 'simulated', True, False),
            client=client,
            models=object(),
            inference_lock=threading.Lock(),
            configuration=configuration,
            pipeline_factory=FakePipeline,
            capture_factory=lambda _source: FailedCapture(),
        )
        client.worker = worker

        worker.start()
        worker.join(1)

        states = [item['state'] for item in client.heartbeats]
        self.assertIn('reconnecting', states)
        self.assertIn('offline', states)
        self.assertEqual(states[-1], 'stopped')

    def test_side_camera_submits_official_analytics(self):
        client = FakeBackendClient()
        configuration = ControllerConfiguration(
            cameras=(), poll_seconds=0.01, heartbeat_seconds=0.01,
            summary_seconds=0.01, analysis_hz=8, reconnect_attempts=2,
            reconnect_backoff_seconds=0.01,
        )
        worker = CameraWorker(
            work={
                'session_id': 4, 'camera_id': 2, 'position': 'left',
                'slide_event_id': 10, 'official_analytics': True,
            },
            source=CameraSource('left', 'private.mp4', 'live', False, True),
            client=client,
            models=object(),
            inference_lock=threading.Lock(),
            configuration=configuration,
            pipeline_factory=FakePipeline,
            capture_factory=lambda _source: FrameCapture(),
        )
        client.worker = worker

        worker.start()
        worker.join(1)

        self.assertFalse(worker.is_alive())
        self.assertEqual(len(client.submissions), 1)
        self.assertEqual(client.submissions[0]['camera_id'], 2)


class WorkerStartupTests(unittest.TestCase):
    def setUp(self):
        self.processing = threading.Event()
        self.release_processing = threading.Event()
        self.repeated_heartbeat = threading.Event()
        self.timed_out = threading.Event()
        self.client = FakeBackendClient()
        heartbeat = self.client.heartbeat

        def receive(payload):
            result = heartbeat(payload)
            if sum(item['state'] == 'starting' for item in self.client.heartbeats) >= 3:
                self.repeated_heartbeat.set()
            if payload['state'] == 'offline':
                self.timed_out.set()
            return result

        self.client.heartbeat = receive
        self.pipeline = FakePipeline(object())
        process = self.pipeline.process_frame

        def slow_process(frame, timestamp):
            self.processing.set()
            self.assertTrue(self.release_processing.wait(3))
            return process(frame, timestamp)

        self.pipeline.process_frame = slow_process
        self.capture = FrameCapture()
        self.worker = CameraWorker(
            work={'session_id': 4, 'camera_id': 1, 'position': 'front', 'slide_event_id': None},
            source=CameraSource('front', 'fixture.mp4', 'simulated', False, True),
            client=self.client, models=object(), inference_lock=threading.Lock(),
            configuration=ControllerConfiguration(cameras=(), heartbeat_seconds=0.01),
            pipeline_factory=lambda _models: self.pipeline,
            capture_factory=lambda _source: self.capture,
        )
        self.client.worker = self.worker
        self.addCleanup(self.close_worker)

    def close_worker(self):
        self.worker.stop()
        self.release_processing.set()
        if self.worker.thread.ident is not None:
            self.worker.join(2)

    def test_starting_heartbeats_continue_during_slow_first_frame(self):
        self.worker.start()
        self.assertTrue(self.processing.wait(1))
        self.assertTrue(self.repeated_heartbeat.wait(1))
        self.assertNotIn('online', [item['state'] for item in self.client.heartbeats])

        self.release_processing.set()
        self.worker.join(1)

        self.assertFalse(self.worker.is_alive())
        self.assertIn('online', [item['state'] for item in self.client.heartbeats])
        self.assertEqual(self.client.heartbeats[-1]['state'], 'stopped')

    def test_starting_heartbeats_continue_while_waiting_for_shared_inference(self):
        self.worker.inference_lock.acquire()
        self.worker.start()
        try:
            self.assertTrue(self.repeated_heartbeat.wait(1))
            self.assertFalse(self.processing.is_set())
            self.assertNotIn('online', [item['state'] for item in self.client.heartbeats])
        finally:
            self.worker.inference_lock.release()
            self.release_processing.set()
        self.worker.join(1)
        self.assertFalse(self.worker.is_alive())

    @patch('tagad_pipeline.controller.STARTUP_TIMEOUT_SECONDS', 0.05)
    def test_startup_timeout_reports_failure_and_recovers_in_legal_order(self):
        self.worker.start()
        self.assertTrue(self.processing.wait(1))
        self.assertTrue(self.timed_out.wait(1))
        self.assertEqual(self.client.heartbeats[-1]['reason'], 'retry_exhausted')

        self.release_processing.set()
        self.worker.join(1)

        self.assertFalse(self.worker.is_alive())
        states = [item['state'] for item in self.client.heartbeats]
        online = states.index('online')
        self.assertEqual(states[online - 1], 'starting')
        self.assertIn('offline', states[:online])
        self.assertEqual(states[online:], ['online', 'stopped'])

    def test_cancellation_joins_startup_reporter_without_announcing_online(self):
        self.worker.start()
        self.assertTrue(self.processing.wait(1))
        self.assertTrue(self.repeated_heartbeat.wait(1))
        self.worker.stop('session_ended')
        self.release_processing.set()
        self.worker.join(1)

        self.assertFalse(self.worker.is_alive())
        self.assertNotIn('online', [item['state'] for item in self.client.heartbeats])
        self.assertEqual(self.client.heartbeats[-1]['reason'], 'session_ended')
        self.assertFalse(any(thread.name == 'camera-startup-4-1' for thread in threading.enumerate()))

    def test_first_decoded_frame_is_processed_before_sampling_later_frames(self):
        self.capture.get = lambda _property: 240
        self.release_processing.set()
        self.worker.start()
        self.assertTrue(self.processing.wait(1))
        self.worker.join(1)
        self.assertFalse(self.worker.is_alive())
        self.assertIn('online', [item['state'] for item in self.client.heartbeats])

    def test_failed_registration_recovers_before_announcing_online(self):
        heartbeat = self.client.heartbeat
        failed_registrations = []

        def temporary_failure(payload):
            if payload['state'] == 'starting' and len(failed_registrations) < 2:
                failed_registrations.append(payload)
                raise BackendRequestError('temporarily unavailable')
            if payload['state'] == 'online':
                self.assertTrue(self.worker.registered)
            return heartbeat(payload)

        self.client.heartbeat = temporary_failure
        self.release_processing.set()
        self.worker.start()
        self.worker.join(1)
        self.assertFalse(self.worker.is_alive())
        self.assertEqual(len(failed_registrations), 2)
        self.assertIn('online', [item['state'] for item in self.client.heartbeats])


if __name__ == '__main__':
    unittest.main()
