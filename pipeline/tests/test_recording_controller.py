import io
import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tagad_pipeline.backend_client import BackendRequestError
from tagad_pipeline.configuration import CameraSource, ControllerConfiguration
from tagad_pipeline.recording_controller import RecordingController, SessionRecording
from tagad_pipeline.controller import CameraController, open_capture
from test_controller import FakeControllerWorker


class FakeRecording:
    def __init__(self, session, sources, args, av):
        self.session = dict(session)
        self.sources = sources
        self.alive = False
        self.joined = False

    def start(self):
        self.alive = True

    def stop(self, reason):
        self.session['stop_reason'] = reason
        self.alive = False

    def is_alive(self):
        return self.alive

    def join(self):
        self.joined = True


class RecordingControllerTests(unittest.TestCase):
    def setUp(self):
        self.configuration = ControllerConfiguration(tuple(
            CameraSource(position, f'rtsp://admin:secret@192.0.2.{index}/stream1', 'live', False, True)
            for index, position in enumerate(('front', 'left', 'right'), start=1)
        ))
        self.factory = Mock(side_effect=FakeRecording)
        self.client = Mock()
        self.controller = RecordingController(self.client, self.configuration, object(), object(), self.factory)
        self.session = {
            'session_id': 7, 'classroom_id': 3, 'active': True,
            'started_at': '2026-11-06T10:00:00Z', 'slide_event_id': 10,
            'cameras': [
                {'camera_id': index, 'position': position, 'ip_address': f'192.0.2.{index}'}
                for index, position in enumerate(('front', 'left', 'right'), start=1)
            ],
        }

    def test_prepared_sessions_wait_then_start_once_and_stop_at_end(self):
        self.controller.reconcile([dict(self.session, active=False, started_at=None)])
        self.factory.assert_not_called()

        self.controller.reconcile([self.session])
        job = self.controller.job
        self.assertTrue(job.alive)
        self.assertEqual([source.position for source in job.sources], ['front', 'left', 'right'])
        self.controller.reconcile([dict(self.session, slide_event_id=20)])
        self.factory.assert_called_once()

        self.controller.reconcile([])
        self.assertTrue(job.joined)
        self.assertEqual(job.session['stop_reason'], 'session_ended')
        self.assertIsNone(self.controller.job)
        self.controller.reconcile([self.session])
        self.factory.assert_called_once()
        self.controller.reconcile([dict(self.session, session_id=8)])
        self.assertEqual(self.factory.call_count, 2)

    def test_only_assigned_matching_cameras_record(self):
        self.session['cameras'] = self.session['cameras'][1:2]
        self.controller.reconcile([self.session])
        self.assertEqual([source.position for source in self.controller.job.sources], ['left'])

    def test_missing_unknown_mismatched_and_duplicate_sources_do_not_record(self):
        for cameras in (
            [],
            [{'position': 'front', 'ip_address': None}],
            [{'position': 'front', 'ip_address': '192.0.2.99'}],
            [{'position': 'left', 'ip_address': '192.0.2.1'}],
            [self.session['cameras'][0], self.session['cameras'][0]],
        ):
            with self.subTest(cameras=cameras):
                self.controller.retry_after.clear()
                with redirect_stdout(io.StringIO()):
                    self.controller.reconcile([dict(self.session, cameras=cameras)])
                self.factory.assert_not_called()

    def test_failed_job_retries_after_backoff(self):
        with patch('tagad_pipeline.recording_controller.time.monotonic', return_value=100):
            self.controller.reconcile([self.session])
            self.controller.job.alive = False
            self.controller.reconcile([self.session])
            self.assertIsNone(self.controller.job)
            self.factory.assert_called_once()
        with patch('tagad_pipeline.recording_controller.time.monotonic', return_value=131):
            self.controller.reconcile([self.session])
        self.assertEqual(self.factory.call_count, 2)

    def test_backend_failure_closes_capture_then_restarts_on_recovery(self):
        for error in (BackendRequestError('unavailable'), TimeoutError()):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                stop_file = Path(directory) / 'stop'
                jobs = []
                self.controller.job = None

                def work():
                    if not jobs:
                        return {'sessions': [self.session]}
                    if len(jobs) == 1 and jobs[0].alive:
                        raise error
                    if len(jobs) == 1:
                        return {'sessions': [self.session]}
                    stop_file.touch()
                    return {'sessions': [self.session]}

                def create(*args):
                    job = FakeRecording(*args)
                    jobs.append(job)
                    return job

                self.factory.side_effect = create
                self.client.work.side_effect = work
                with patch('tagad_pipeline.recording_controller.time.sleep'), redirect_stdout(io.StringIO()):
                    self.controller.wait_for_sessions(stop_file)
                self.assertEqual(len(jobs), 2)
                self.assertEqual(jobs[0].session['stop_reason'], 'backend_unavailable')
                self.assertEqual(jobs[1].session['stop_reason'], 'shutdown')
                self.assertTrue(all(job.joined for job in jobs))

    def test_recording_thread_passes_lifecycle_stop_and_session_metadata(self):
        job = SessionRecording(self.session, self.configuration.cameras, object(), object())
        with patch('tagad_pipeline.recording_controller.run', return_value=0) as record:
            job.start()
            job.join()
        self.assertEqual(job.exit_status, 0)
        self.assertIs(record.call_args.args[3], job.stop_event)
        self.assertEqual(record.call_args.args[4]['session_id'], 7)
        job.stop('session_ended')
        job.stop('shutdown')
        self.assertTrue(job.stop_event.is_set())
        self.assertEqual(job.session['stop_reason'], 'session_ended')

    def test_save_and_continue_make_separate_playable_three_camera_recordings(self):
        import av
        import numpy as np

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / 'synthetic.mp4'
            with av.open(str(fixture), mode='w') as output:
                stream = output.add_stream('libx264', rate=15)
                stream.width, stream.height, stream.pix_fmt = 64, 64, 'yuv420p'
                for _index in range(150):
                    frame = av.VideoFrame.from_ndarray(np.zeros((64, 64, 3), dtype=np.uint8), format='rgb24')
                    for packet in stream.encode(frame):
                        output.mux(packet)
                for packet in stream.encode():
                    output.mux(packet)

            import cv2
            real_capture = cv2.VideoCapture

            def synthetic_capture(_source, backend, options):
                return real_capture(str(fixture), backend, options)

            with patch('tagad_pipeline.controller.cv2.VideoCapture', side_effect=synthetic_capture):
                capture = open_capture('rtsp://camera.invalid/stream1')
                try:
                    self.assertTrue(capture.isOpened())
                    self.assertTrue(capture.read()[0])
                finally:
                    capture.release()

            positions = {source.source: source.position for source in self.configuration.cameras}
            received = {position: 0 for position in positions.values()}
            counter_lock = threading.Lock()
            real_open = av.open

            class SyntheticLiveInput:
                def __init__(self, position):
                    self.position = position
                    self.container = real_open(str(fixture))
                    self.streams = self.container.streams

                def __enter__(self):
                    return self

                def __exit__(self, *_arguments):
                    self.container.close()

                def demux(self, stream):
                    for packet in self.container.demux(stream):
                        has_payload = bool(packet.size)
                        yield packet
                        if has_payload:
                            with counter_lock:
                                received[self.position] += 1
                        time.sleep(0.01)

            def synthetic_open(file, *arguments, **options):
                if isinstance(file, str) and file in positions:
                    return SyntheticLiveInput(positions[file])
                return real_open(file, *arguments, **options)

            def wait_for_video():
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    with counter_lock:
                        if all(count >= 5 for count in received.values()):
                            return
                    time.sleep(0.01)
                self.fail('Synthetic camera workers did not write video in time.')

            args = SimpleNamespace(output_root=root / 'private-recordings', minutes=60)
            recorder = RecordingController(self.client, self.configuration, args, av)
            processing = CameraController(
                client=object(), models=object(), configuration=self.configuration,
                worker_factory=FakeControllerWorker,
            )

            def reconcile(sessions):
                processing.reconcile(sessions)
                recorder.reconcile(sessions)

            def close_meeting():
                job = recorder.job
                reconcile([])
                job.join(10)
                self.assertFalse(job.is_alive())
                reconcile([])
                self.assertIsNone(recorder.job)
                self.assertFalse(processing.workers)

            with patch('av.open', side_effect=synthetic_open), redirect_stdout(io.StringIO()):
                try:
                    prepared = dict(self.session, active=False, started_at=None, slide_event_id=None)
                    reconcile([prepared])
                    self.assertEqual(len(processing.workers), 3)
                    self.assertIsNone(recorder.job)
                    self.assertFalse(args.output_root.exists())

                    reconcile([self.session])
                    wait_for_video()
                    close_meeting()
                    first_folder = next(args.output_root.iterdir())
                    original_files = {path.name: path.read_bytes() for path in first_folder.iterdir()}

                    continuation = dict(prepared, session_id=8)
                    reconcile([continuation])
                    self.assertIsNone(recorder.job)
                    self.assertEqual(len(list(args.output_root.iterdir())), 1)
                    with counter_lock:
                        received.update({position: 0 for position in received})
                    reconcile([dict(continuation, active=True, started_at='2026-11-07T10:00:00Z', slide_event_id=20)])
                    self.assertEqual({worker.work['session_id'] for worker in processing.workers.values()}, {8})
                    self.assertEqual({worker.work['slide_event_id'] for worker in processing.workers.values()}, {20})
                    wait_for_video()
                    close_meeting()
                finally:
                    recorder.shutdown()
                    processing.shutdown()

            folders = list(args.output_root.iterdir())
            self.assertEqual(len(folders), 2)
            self.assertEqual(original_files, {path.name: path.read_bytes() for path in first_folder.iterdir()})
            recorded_ids = set()
            for folder in folders:
                manifest = json.loads((folder / 'recording-manifest.json').read_text())
                recorded_ids.add(manifest['session_id'])
                self.assertEqual(manifest['status'], 'completed')
                self.assertEqual(manifest['stop_reason'], 'session_ended')
                self.assertEqual(len(manifest['cameras']), 3)
                for camera in manifest['cameras']:
                    video_path = folder / camera['segments'][0]['file']
                    with real_open(str(video_path)) as video:
                        self.assertFalse(video.streams.audio)
                        self.assertGreater(sum(1 for _frame in video.decode(video=0)), 0)
            self.assertEqual(recorded_ids, {7, 8})


if __name__ == '__main__':
    unittest.main()
