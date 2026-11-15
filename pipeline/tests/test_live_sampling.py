import io
import threading
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from tagad_pipeline.configuration import CameraSource, ControllerConfiguration
from tagad_pipeline.controller import CameraWorker
from tagad_pipeline.worker import parser, run


class TimedCapture:
    def __init__(self, advertised_fps, processing_seconds=0):
        self.advertised_fps = advertised_fps
        self.processing_seconds = processing_seconds
        self.index, self.now = 0, 0.0
        self.worker = None

    def isOpened(self):
        return True

    def get(self, _property):
        return self.advertised_fps

    def read(self):
        if self.index == 100:
            if self.worker:
                self.worker.stop('session_ended')
            return False, None
        self.now = max(self.now, self.index / 10)
        self.index += 1
        return True, object()

    def release(self):
        pass


class SamplingPipeline:
    def __init__(self, capture):
        self.capture = capture
        self.times = []

    def process_frame(self, _frame, timestamp):
        self.times.append(timestamp)
        self.capture.now += self.capture.processing_seconds
        return SimpleNamespace(predictions=[], yolo_candidates=0, valid_faces=0, confirmed_students=0)


class LiveSamplingTests(unittest.TestCase):
    def run_controller(self, advertised_fps, source_type='live', processing_seconds=0):
        capture = TimedCapture(advertised_fps, processing_seconds)
        pipeline = SamplingPipeline(capture)
        worker = CameraWorker(
            work={'session_id': 4, 'camera_id': 1, 'position': 'front', 'slide_event_id': None},
            source=CameraSource('front', 'rtsp://camera.invalid/stream1', source_type, False, True),
            client=SimpleNamespace(heartbeat=lambda payload: payload), models=object(),
            inference_lock=threading.Lock(), configuration=ControllerConfiguration(cameras=(), analysis_hz=2.5),
            clock=lambda: capture.now, capture_factory=lambda _source: capture,
            pipeline_factory=lambda _models: pipeline,
        )
        capture.worker = worker
        with redirect_stdout(io.StringIO()):
            worker.run()
        return pipeline.times

    def test_live_controller_uses_elapsed_time_when_nominal_fps_is_wrong(self):
        for advertised in (0, 15, 25, float('nan')):
            with self.subTest(advertised_fps=advertised):
                times = self.run_controller(advertised)
                self.assertEqual(len(times), 25)
                self.assertEqual(times[:3], [0.0, 0.4, 0.8])

    def test_simulated_controller_retains_its_frame_sampling(self):
        self.assertEqual(len(self.run_controller(25, 'simulated')), 11)

    def test_slow_processing_does_not_schedule_catch_up_bursts(self):
        times = self.run_controller(25, processing_seconds=0.7)
        self.assertTrue(all(b - a >= 0.7 - 1e-9 for a, b in zip(times, times[1:])))

    def test_standalone_live_rate_and_recorded_frame_sampling(self):
        for source, advertised, count, first_times in (
            ('rtsp://camera.invalid/stream1', 15, 25, [0.0, 0.4, 0.8]),
            ('rtsp://camera.invalid/stream1', 25, 25, [0.0, 0.4, 0.8]),
            ('recorded.mp4', 25, 10, [0.4, 0.8, 1.2]),
        ):
            with self.subTest(source=source, advertised_fps=advertised):
                capture = TimedCapture(advertised)
                pipeline = SamplingPipeline(capture)
                args = parser().parse_args([
                    '--source', source, '--dry-run', '--analysis-hz', '2.5',
                ])
                with (
                    patch('tagad_pipeline.worker.verify_artifacts'),
                    patch('tagad_pipeline.worker.ModelBundle', return_value=SimpleNamespace(close=lambda: None)),
                    patch('tagad_pipeline.worker.CameraPipeline', return_value=pipeline),
                    patch('tagad_pipeline.worker.cv2.VideoCapture', return_value=capture),
                    patch('tagad_pipeline.worker.time.monotonic', side_effect=lambda: capture.now),
                    redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(run(args), 0)
                self.assertEqual(len(pipeline.times), count)
                self.assertEqual(pipeline.times[:3], first_times)


if __name__ == '__main__':
    unittest.main()
