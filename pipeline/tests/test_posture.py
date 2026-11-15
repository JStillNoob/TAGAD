import json
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tagad_pipeline.posture import PostureMetrics, posture_features
from tagad_pipeline.posture_benchmark import parser, recording_timing, run, validate_inputs
from tagad_pipeline.tracking import Track


def person():
    points = [[0.0, 0.0, 0.0] for _ in range(17)]
    for index, position in {
        5: (30, 30), 6: (70, 30), 7: (30, 50), 8: (70, 50),
        9: (30, 70), 10: (70, 70), 11: (35, 80), 12: (65, 80),
    }.items():
        points[index] = [*position, 0.9]
    return {'box': [0, 0, 100, 100], 'keypoints': points}


class PostureTests(unittest.TestCase):
    def setUp(self):
        self.track = Track(91, (40, 5, 60, 25), 0, 0)

    def test_features_and_temporal_readiness_use_source_time(self):
        metrics = PostureMetrics()
        for index in range(9):
            metrics.update([self.track], [person()], index * 0.4, 100, 100)
        report = metrics.summary()
        self.assertEqual(report['counts']['matched'], 9)
        self.assertEqual(report['joints']['left_shoulder']['usable_observations'], 9)
        self.assertAlmostEqual(report['joints']['left_shoulder']['mean'], 0.9)
        self.assertEqual(report['features']['left_elbow_angle']['samples'], 1)
        self.assertAlmostEqual(report['features']['left_elbow_angle']['mean'], 180)
        self.assertAlmostEqual(report['features']['torso_lean']['mean'], 0)
        self.assertNotIn('track_id', json.dumps(report))
        self.assertEqual(report['feasibility'], 'unverified')

    def test_ambiguous_pairings_and_history_gaps_do_not_force_features(self):
        metrics = PostureMetrics()
        metrics.update([self.track], [person(), person()], 0, 100, 100)
        self.assertEqual(metrics.summary()['counts']['ambiguous'], 1)
        for index in range(9):
            metrics.update([self.track], [person()], index * 0.4, 100, 100)
        ready = metrics.summary()['features']['shoulder_tilt']['samples']
        metrics.update([self.track], [person()], 5, 100, 100)
        self.assertEqual(metrics.summary()['features']['shoulder_tilt']['samples'], ready)
        metrics.update([], [], 5.4, 100, 100)
        self.assertFalse(metrics.histories)
        self.assertFalse(metrics.previous_wrists)

    def test_multiple_heads_in_one_person_box_are_rejected(self):
        metrics = PostureMetrics()
        other = Track(92, (10, 5, 30, 25), 0, 0)
        metrics.update([self.track, other], [person()], 0, 100, 100)
        self.assertEqual(metrics.summary()['counts']['ambiguous'], 2)

    def test_torso_stability_handles_angle_wrap(self):
        metrics = PostureMetrics()
        for index in range(9):
            observation = person()
            offset = 0.1 if index % 2 else -0.1
            observation['keypoints'][11] = [35 + offset, 20, 0.9]
            observation['keypoints'][12] = [65 + offset, 20, 0.9]
            metrics.update([self.track], [observation], index * 0.4, 100, 100)
        torso = metrics.summary()['features']['torso_lean']
        self.assertGreater(abs(torso['mean']), 179)
        self.assertLess(torso['mean_window_std'], 1)

    def test_invalid_joints_and_degenerate_scale_stay_missing(self):
        invalid = person()
        invalid['keypoints'][5][2] = 0.1
        invalid['keypoints'][7][0] = math.nan
        invalid['keypoints'][9][0] = 101
        invalid['keypoints'][11] = [35, 80]
        metrics = PostureMetrics()
        metrics.update([self.track], [invalid], 0, 100, 100)
        counts = metrics.summary()['counts']
        for reason in ('joint_low_confidence', 'joint_nonfinite', 'joint_out_of_frame', 'joint_missing_confidence'):
            self.assertEqual(counts[reason], 1)
        features, scale, _wrists = posture_features({5: (1, 1), 6: (1, 1)})
        self.assertEqual(features, {})
        self.assertIsNone(scale)


class FakeCapture:
    frame_limit = 50

    def __init__(self, _source):
        self.index = 0
        self.streams = SimpleNamespace(video=[SimpleNamespace(
            average_rate=Fraction(10), time_base=Fraction(1, 10), duration=50,
        )])

    def decode(self, video=0):
        while self.index < self.frame_limit:
            frame = SimpleNamespace(
                pts=self.index, time_base=Fraction(1, 10), duration=1,
                width=100, height=100,
                to_ndarray=lambda **_options: SimpleNamespace(shape=(100, 100, 3)),
            )
            self.index += 1
            yield frame

    def seek(self, *_args, **_options):
        self.index = 0

    def close(self):
        pass


class InterruptedCapture(FakeCapture):
    frame_limit = 3


class FakePipeline:
    def __init__(self, _models):
        self.tracker = SimpleNamespace(tracks={1: Track(1, (40, 5, 60, 25), 0, 0)})

    def process_frame(self, _frame, _timestamp):
        return SimpleNamespace(
            yolo_candidates=1, valid_faces=1, confirmed_students=1,
            predictions=[{'label': 'Engaged', 'confidence': 0.8}],
        )


class FakePose:
    task = 'pose'

    def predict(self, _frame, **_kwargs):
        observation = person()
        boxes = SimpleNamespace(cpu=lambda: SimpleNamespace(tolist=lambda: [observation['box']]))
        points = SimpleNamespace(cpu=lambda: SimpleNamespace(tolist=lambda: [observation['keypoints']]))
        return [SimpleNamespace(boxes=SimpleNamespace(xyxy=boxes), keypoints=SimpleNamespace(data=points))]


class OfflineEvaluatorTests(unittest.TestCase):
    def make_args(self, root, mode='pose'):
        cameras = []
        for camera in ('front', 'left', 'right'):
            video = root / f'{camera}.mp4'
            video.touch()
            cameras.append({'position': camera, 'source': str(video), 'source_type': 'simulated'})
        config = root / 'sources.json'
        config.write_text(json.dumps({'cameras': cameras}), encoding='utf-8')
        checkpoint = root / 'candidate.pt'
        checkpoint.write_bytes(b'synthetic-checkpoint')
        return parser().parse_args([
            '--config', str(config), '--pose-model', str(checkpoint),
            '--output', str(root / f'{mode}.json'), '--mode', mode, '--source-seconds', '5',
        ])

    def test_rejects_live_inputs_missing_weights_and_nonfinite_options(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            for name in ('analysis_hz', 'source_seconds', 'joint_confidence'):
                original = getattr(args, name)
                setattr(args, name, math.nan)
                with self.assertRaises(ValueError):
                    validate_inputs(args)
                setattr(args, name, original)
            args.pose_model.unlink()
            with self.assertRaises(ValueError):
                validate_inputs(args)
            args.mode = 'baseline'
            args.config.write_text(json.dumps({'cameras': [{
                'position': 'front', 'source': 'rtsp://private:secret@example.invalid/stream',
                'source_type': 'live',
            }]}), encoding='utf-8')
            with self.assertRaises(ValueError) as error:
                validate_inputs(args)
            self.assertNotIn('secret', str(error.exception))

    def test_recording_timing_requires_matching_valid_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = SimpleNamespace(position='right', source=str(root / 'right-01.mp4'))
            self.assertIsNone(recording_timing(source))
            path = root / 'recording-manifest.json'
            segment = {'file': 'right-01.mp4'}
            manifest = {'cameras': [{'camera': 'right', 'segments': [segment]}]}
            path.write_text(json.dumps(manifest))
            self.assertEqual(recording_timing(source)['corrected_timestamp_packets'], 0)
            for key, value in (
                ('corrected_timestamp_packets', -1), ('corrected_timestamp_packets', True),
                ('max_timestamp_adjustment_seconds', float('nan')),
            ):
                segment[key] = value
                path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    recording_timing(source)
                segment.pop(key)
            segment['file'] = 'front-01.mp4'
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                recording_timing(source)

    def test_normal_entry_runs_three_cameras_with_synthetic_models_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mode in ('baseline', 'pose'):
                args = self.make_args(root, mode)
                sources = validate_inputs(args)
                (root / 'recording-manifest.json').write_text(json.dumps({'cameras': [
                    {'camera': source.position, 'segments': [{
                        'file': Path(source.source).name, 'corrected_timestamp_packets': 3,
                        'tail_estimated_timestamp_packets': 1, 'max_timestamp_adjustment_seconds': 0.1,
                    }]} for source in sources
                ]}), encoding='utf-8')
                fake_models = SimpleNamespace(device='cpu', close=lambda: None)
                with (
                    patch('av.open', FakeCapture),
                    patch('tagad_pipeline.inference.CameraPipeline', FakePipeline),
                    patch('tagad_pipeline.inference.ModelBundle', return_value=fake_models),
                    patch('tagad_pipeline.posture_benchmark.verify_artifacts', return_value={'pipeline_version': 'synthetic'}),
                    patch('ultralytics.YOLO', return_value=FakePose()),
                ):
                    self.assertEqual(run(args, sources), 0)
                report = json.loads(args.output.read_text(encoding='utf-8'))
                self.assertEqual(len(report['cameras']), 3)
                self.assertEqual(report['human_review'], 'pending')
                self.assertIsNone(report['combined_student_count'])
                for source in report['inputs']:
                    self.assertEqual(source['recording_timing']['corrected_timestamp_packets'], 3)
                    self.assertEqual(source['recording_timing']['tail_estimated_timestamp_packets'], 1)
                    self.assertEqual(source['recording_timing']['max_timestamp_adjustment_seconds'], 0.1)
                    self.assertEqual(len(source['recording_timing']['manifest_sha256']), 64)
                for camera in report['cameras']:
                    self.assertEqual(camera['analyzed_frames'], 13)
                    self.assertEqual(camera['source_seconds_read'], 5)
                    self.assertEqual(camera['status'], 'completed')
                    self.assertEqual(camera['posture'] is None, mode == 'baseline')
                for forbidden in ('track_id', 'keypoints', 'synthetic-checkpoint', str(root)):
                    self.assertNotIn(forbidden, json.dumps(report))
                with self.assertRaises(ValueError):
                    validate_inputs(args)

    def test_interrupted_recording_produces_failed_aggregate_report(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory), 'baseline')
            sources = validate_inputs(args)
            with (
                patch('av.open', InterruptedCapture),
                patch('tagad_pipeline.inference.CameraPipeline', FakePipeline),
                patch('tagad_pipeline.inference.ModelBundle', return_value=SimpleNamespace(device='cpu', close=lambda: None)),
                patch('tagad_pipeline.posture_benchmark.verify_artifacts', return_value={'pipeline_version': 'synthetic'}),
            ):
                self.assertEqual(run(args, sources), 1)
            report = json.loads(args.output.read_text(encoding='utf-8'))
            self.assertTrue(all(camera['status'] == 'failed' for camera in report['cameras']))
            self.assertEqual(report['feasibility'], 'unverified')

    def test_variable_frame_rate_uses_real_presentation_times_through_normal_entry(self):
        from test_camera_recording import create_timed_video

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self.make_args(root, 'baseline')
            timestamps = [index * 75 - (25 if index % 2 else 0) for index in range(90)]
            sources = validate_inputs(args)
            create_timed_video(Path(sources[0].source), timestamps)
            for source in sources[1:]:
                Path(source.source).write_bytes(Path(sources[0].source).read_bytes())
            observations = []

            class TimedPipeline(FakePipeline):
                def __init__(self, models):
                    super().__init__(models)
                    self.times = []
                    observations.append(self.times)

                def process_frame(self, frame, timestamp):
                    self.times.append(timestamp)
                    return super().process_frame(frame, timestamp)

            with (
                patch('tagad_pipeline.inference.CameraPipeline', TimedPipeline),
                patch('tagad_pipeline.inference.ModelBundle', return_value=SimpleNamespace(device='cpu', close=lambda: None)),
                patch('tagad_pipeline.posture_benchmark.verify_artifacts', return_value={'pipeline_version': 'synthetic'}),
            ):
                self.assertEqual(run(args, sources), 0)
            for times in observations[1:]:
                self.assertEqual(times[:3], [0.0, 0.45, 0.8])
                self.assertTrue(all(0 <= timestamp < 5 for timestamp in times))
            report = json.loads(args.output.read_text())
            self.assertTrue(all(camera['source_seconds_read'] == 5 for camera in report['cameras']))
            self.assertTrue(all('presentation timestamps' in camera['timestamp_basis'] for camera in report['cameras']))

    def test_missing_or_repeated_presentation_timestamps_fail_evaluation(self):
        for invalid_timestamp in (None, 0):
            with self.subTest(timestamp=invalid_timestamp), tempfile.TemporaryDirectory() as directory:
                args = self.make_args(Path(directory), 'baseline')
                sources = validate_inputs(args)

                class BrokenCapture(FakeCapture):
                    def decode(self, video=0):
                        for index, frame in enumerate(super().decode(video)):
                            if index == 1:
                                frame.pts = invalid_timestamp
                            yield frame

                with (
                    patch('av.open', BrokenCapture),
                    patch('tagad_pipeline.inference.CameraPipeline', FakePipeline),
                    patch('tagad_pipeline.inference.ModelBundle', return_value=SimpleNamespace(device='cpu', close=lambda: None)),
                    patch('tagad_pipeline.posture_benchmark.verify_artifacts', return_value={'pipeline_version': 'synthetic'}),
                ):
                    self.assertEqual(run(args, sources), 1)
                report = json.loads(args.output.read_text())
                self.assertTrue(all(camera['status'] == 'failed' for camera in report['cameras']))

    def test_container_duration_supports_files_without_stream_duration(self):
        class ContainerDurationCapture(FakeCapture):
            def __init__(self, source):
                super().__init__(source)
                self.streams.video[0].duration = None
                self.duration = 5_000_000

        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory), 'baseline')
            sources = validate_inputs(args)
            with (
                patch('av.open', ContainerDurationCapture),
                patch('tagad_pipeline.inference.CameraPipeline', FakePipeline),
                patch('tagad_pipeline.inference.ModelBundle', return_value=SimpleNamespace(device='cpu', close=lambda: None)),
                patch('tagad_pipeline.posture_benchmark.verify_artifacts', return_value={'pipeline_version': 'synthetic'}),
            ):
                self.assertEqual(run(args, sources), 0)

    def test_audio_only_input_is_rejected_before_model_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory), 'baseline')
            sources = validate_inputs(args)
            capture = FakeCapture('unused')
            capture.streams.video = []
            with patch('av.open', return_value=capture), patch('tagad_pipeline.inference.ModelBundle') as models:
                with self.assertRaisesRegex(ValueError, 'no video stream'):
                    run(args, sources)
                models.assert_not_called()


if __name__ == '__main__':
    unittest.main()
