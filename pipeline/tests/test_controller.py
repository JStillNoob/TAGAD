import threading
import time
import unittest
from types import SimpleNamespace

from tagad_pipeline.configuration import CameraSource, ControllerConfiguration
from tagad_pipeline.controller import CameraController, CameraWorker


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
                {'camera_id': 2, 'position': 'left', 'official_analytics': False},
                {'camera_id': 3, 'position': 'right', 'official_analytics': False},
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

    def test_removed_session_stops_all_its_workers(self):
        self.controller.reconcile([self.session])
        workers = list(self.controller.workers.values())

        self.controller.reconcile([])

        self.assertFalse(self.controller.workers)
        self.assertTrue(all(worker.stopped_with == 'session_ended' for worker in workers))


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
        pass

    def process_frame(self, _frame, _timestamp):
        return SimpleNamespace(
            predictions=[{'label': 'Engaged', 'confidence': 0.9, 'track_id': 1}],
            yolo_candidates=1,
            valid_faces=1,
            confirmed_students=1,
        )


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

    def test_side_camera_never_submits_official_analytics(self):
        client = FakeBackendClient()
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
        self.assertEqual(client.submissions, [])


if __name__ == '__main__':
    unittest.main()
