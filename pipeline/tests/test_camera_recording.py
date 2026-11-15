import io
import json
import math
import tempfile
import threading
import unittest
from fractions import Fraction
from contextlib import redirect_stdout
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tagad_pipeline.camera_recording import REPO_ROOT, main, parser, record_camera, record_segment, run, validate_inputs


def create_timed_video(path, timestamps):
    import av
    import numpy as np

    with av.open(str(path), mode='w') as output:
        stream = output.add_stream('libx264', rate=15, options={'bf': '0'})
        stream.width, stream.height, stream.pix_fmt = 64, 64, 'yuv420p'
        stream.time_base = stream.codec_context.time_base = Fraction(1, 1000)
        for timestamp in timestamps:
            frame = av.VideoFrame.from_ndarray(np.zeros((64, 64, 3), dtype=np.uint8), format='rgb24')
            frame.pts, frame.time_base = timestamp, Fraction(1, 1000)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)


class CameraRecordingTests(unittest.TestCase):
    def make_args(self, root):
        config = root / 'private-sources.json'
        config.write_text(json.dumps({'cameras': [
            {
                'position': position, 'source_type': 'live',
                'source': f'rtsp://admin:private-password@192.0.2.{index}/stream1',
            }
            for index, position in enumerate(('front', 'left', 'right'), start=1)
        ]}), encoding='utf-8')
        return parser().parse_args(['--config', str(config), '--output-root', str(root / 'private-videos')])

    def test_rejects_repository_storage_and_invalid_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            for duration in (0, -1, math.nan, math.inf, 181):
                args.minutes = duration
                with self.assertRaises(ValueError):
                    validate_inputs(args)
            args.minutes = 60
            args.output_root = REPO_ROOT / 'private_pilot_data'
            with self.assertRaises(ValueError):
                validate_inputs(args)

    def test_check_command_avoids_camera_connections_and_creating_recordings(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            command = [
                'record', '--config', str(args.config), '--output-root', str(args.output_root), '--check',
            ]
            output = io.StringIO()
            with patch('sys.argv', command), patch('av.open') as open_media, redirect_stdout(output):
                self.assertEqual(main(), 0)
            open_media.assert_not_called()
            self.assertFalse(args.output_root.exists())
            self.assertNotIn('private-password', output.getvalue())

    def test_manifest_has_separate_files_and_no_camera_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            sources = validate_inputs(args)
            fake_result = lambda source, *_args: {
                'camera': source.position, 'status': 'completed',
                'segments': [{'file': f'{source.position}-01.mp4', 'packets': 10}],
            }
            with patch('tagad_pipeline.camera_recording.record_camera', side_effect=fake_result), redirect_stdout(io.StringIO()):
                self.assertEqual(run(args, sources, object()), 0)
                self.assertEqual(run(args, sources, object()), 0)
            manifests = list(args.output_root.glob('*/recording-manifest.json'))
            self.assertEqual(len(manifests), 2)
            for manifest in manifests:
                text = manifest.read_text(encoding='utf-8')
                record = json.loads(text)
                self.assertEqual(record['status'], 'completed')
                self.assertEqual(len(record['cameras']), 3)
                self.assertFalse(record['audio_recorded'])
                self.assertTrue(record['offline_config_ready'])
                self.assertTrue((manifest.parent / 'offline-sources.json').is_file())
                for secret in ('private-password', '192.0.2.', 'rtsp://'):
                    self.assertNotIn(secret, text)

    def test_one_camera_retries_without_claiming_an_uninterrupted_recording(self):
        source = SimpleNamespace(position='left')
        stop = threading.Event()
        with (
            patch('tagad_pipeline.camera_recording.record_segment', side_effect=[
                {'status': 'failed', 'error_code': 'TimeoutError'},
                {'status': 'completed', 'error_code': None},
            ]) as record,
            patch.object(stop, 'wait'),
            redirect_stdout(io.StringIO()),
        ):
            result = record_camera(source, Path('.'), math.inf, stop, object())
        self.assertEqual(record.call_count, 2)
        self.assertEqual(result['status'], 'completed_with_gaps')

    def test_session_end_preserves_reconnection_gap_status(self):
        stop = threading.Event()
        with (
            patch('tagad_pipeline.camera_recording.record_segment', side_effect=[
                {'status': 'failed', 'error_code': 'TimeoutError'},
                {'status': 'stopped', 'error_code': None},
            ]) as record,
            patch.object(stop, 'wait'),
            redirect_stdout(io.StringIO()),
        ):
            result = record_camera(SimpleNamespace(position='left'), Path('.'), math.inf, stop, object(), None)
        self.assertEqual(record.call_count, 2)
        self.assertEqual(result['status'], 'completed_with_gaps')

    def test_automatic_capture_uses_session_end_instead_of_manual_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            args.minutes = 0.001
            sources = validate_inputs(args)
            stop = threading.Event()
            session = {'session_id': 7, 'classroom_id': 3, 'started_at': '2026-11-06T10:00:00Z'}

            def capture(source, folder, deadline, stop_event, av, retries):
                self.assertEqual(deadline, math.inf)
                self.assertIs(stop_event, stop)
                self.assertIsNone(retries)
                session['stop_reason'] = 'session_ended'
                stop.set()
                return {
                    'camera': source.position, 'status': 'stopped',
                    'segments': [{'file': f'{source.position}-01.mp4', 'packets': 10}],
                }

            with patch('tagad_pipeline.camera_recording.record_camera', side_effect=capture), redirect_stdout(io.StringIO()):
                self.assertEqual(run(args, sources, object(), stop, session), 0)
            manifest = json.loads(next(args.output_root.glob('*/recording-manifest.json')).read_text())
            self.assertEqual(manifest['status'], 'completed')
            self.assertEqual(manifest['stop_reason'], 'session_ended')
            self.assertEqual(manifest['session_id'], 7)
            self.assertEqual(manifest['duration_control'], 'session_lifecycle')
            self.assertIsNone(manifest['requested_minutes'])

    def test_partial_capture_is_not_prepared_as_an_aligned_offline_set(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            sources = validate_inputs(args)
            with (
                patch('tagad_pipeline.camera_recording.record_camera', return_value={
                    'camera': 'front', 'status': 'failed', 'segments': [],
                }),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(run(args, sources, object()), 1)
            manifest = next(args.output_root.glob('*/recording-manifest.json'))
            record = json.loads(manifest.read_text(encoding='utf-8'))
            self.assertEqual(record['status'], 'partial')
            self.assertFalse(record['offline_config_ready'])
            self.assertFalse((manifest.parent / 'offline-sources.json').exists())

    def test_variable_frame_times_survive_three_camera_recording_and_prepare_offline_inputs(self):
        import av

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / 'variable.mp4'
            timestamps = [index * 75 - (25 if index % 2 else 0) for index in range(90)]
            create_timed_video(fixture, timestamps)
            args = self.make_args(root)
            sources = validate_inputs(args)
            stop = threading.Event()
            finished = threading.Barrier(3)
            real_open = av.open

            class LiveFixture:
                def __enter__(self):
                    self.container = real_open(str(fixture))
                    self.streams = self.container.streams
                    return self

                def __exit__(self, *_args):
                    self.container.close()

                def demux(self, stream):
                    for packet in self.container.demux(stream):
                        if not packet.size:
                            finished.wait(5)
                            stop.set()
                        yield packet

            def open_fixture(file, *arguments, **options):
                return LiveFixture() if file in {source.source for source in sources} else real_open(file, *arguments, **options)

            with patch('av.open', side_effect=open_fixture), redirect_stdout(io.StringIO()):
                self.assertEqual(run(args, sources, av, stop, {'session_id': 7, 'stop_reason': 'session_ended'}), 0)
            manifest = next(args.output_root.glob('*/recording-manifest.json'))
            data = json.loads(manifest.read_text())
            self.assertTrue(data['offline_config_ready'])
            self.assertTrue((manifest.parent / 'offline-sources.json').is_file())
            for camera in data['cameras']:
                segment = camera['segments'][0]
                self.assertGreater(segment['irregular_timestamp_intervals'], 0)
                self.assertEqual(segment['timestamp_basis'], 'source presentation timestamps')
                with real_open(str(manifest.parent / segment['file'])) as video:
                    actual = [frame.pts * frame.time_base for frame in video.decode(video=0)]
                    self.assertFalse(video.streams.audio)
                self.assertEqual(actual, [Fraction(timestamp, 1000) for timestamp in timestamps])

    def test_backward_decode_timestamps_remain_a_recording_failure(self):
        import av

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / 'source.mp4'
            create_timed_video(fixture, [0, 100, 200])
            real_open = av.open
            source = SimpleNamespace(position='front', source='rtsp://camera.invalid/stream1')

            class BrokenFixture:
                def __enter__(self):
                    self.container = real_open(str(fixture))
                    self.streams = self.container.streams
                    return self

                def __exit__(self, *_args):
                    self.container.close()

                def demux(self, stream):
                    for index, packet in enumerate(self.container.demux(stream)):
                        if index == 1:
                            packet.dts = -1
                        yield packet

            def open_fixture(file, *arguments, **options):
                return BrokenFixture() if file == source.source else real_open(file, *arguments, **options)

            with patch('av.open', side_effect=open_fixture), redirect_stdout(io.StringIO()):
                result = record_segment(source, root / 'recorded.mp4', math.inf, threading.Event(), av)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['error_code'], 'timestamp_discontinuity')

    def test_duplicate_timestamps_preserve_every_frame_and_disclose_estimated_timing(self):
        import av

        for duplicate_indices, ending in (({1, 31, 61}, 'eof'), ({0, 1, 2}, 'eof'), ({88, 89}, 'stop')):
            with self.subTest(duplicates=duplicate_indices, ending=ending), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = root / 'source.mp4'
                create_timed_video(fixture, list(range(0, 9000, 100)))
                real_open = av.open
                source = SimpleNamespace(position='right', source='rtsp://camera.invalid/stream1')
                stop = threading.Event()

                class DuplicateFixture:
                    def __enter__(self):
                        self.container = real_open(str(fixture))
                        self.streams = self.container.streams
                        return self

                    def __exit__(self, *_args):
                        self.container.close()

                    def demux(self, stream):
                        last_source_time = 0
                        for index, packet in enumerate(self.container.demux(stream)):
                            if not packet.size:
                                if ending == 'stop':
                                    stop.set()
                                yield packet
                                continue
                            if index in duplicate_indices:
                                packet.pts = packet.dts = last_source_time
                            else:
                                last_source_time = packet.dts
                            yield packet

                def open_fixture(file, *arguments, **options):
                    return DuplicateFixture() if file == source.source else real_open(file, *arguments, **options)

                with patch('av.open', side_effect=open_fixture), redirect_stdout(io.StringIO()):
                    result = record_segment(source, root / 'recorded.mp4', math.inf, stop, av)
                self.assertEqual(result['error_code'], 'stream_ended' if ending == 'eof' else None)
                self.assertEqual(result['status'], 'failed' if ending == 'eof' else 'stopped')
                self.assertEqual(result['packets'], 90)
                self.assertGreater(result['corrected_timestamp_packets'], 0)
                self.assertIn('estimated', result['timestamp_basis'])
                with real_open(str(root / 'recorded.mp4')) as media:
                    frames = list(media.decode(video=0))
                    times = [frame.pts * frame.time_base for frame in frames]
                    self.assertEqual(len(frames), 90)
                    self.assertTrue(all(b > a for a, b in zip(times, times[1:])))
                    self.assertAlmostEqual(float(times[-1] + frames[-1].duration * frames[-1].time_base), 9, delta=0.12)
                self.assertEqual(result['tail_estimated_timestamp_packets'], 2 if duplicate_indices == {88, 89} else 0)
                with real_open(str(fixture)) as original, real_open(str(root / 'recorded.mp4')) as recorded:
                    self.assertEqual(
                        [bytes(packet) for packet in original.demux(video=0) if packet.size],
                        [bytes(packet) for packet in recorded.demux(video=0) if packet.size],
                    )

    def test_duplicate_repair_refuses_unbounded_or_reordered_timing(self):
        import av

        for scenario in ('too_many', 'wide_gap', 'reordered_pts', 'insufficient_ticks'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = root / 'source.mp4'
                create_timed_video(fixture, list(range(0, 1500, 100)))
                real_open = av.open
                source = SimpleNamespace(position='right', source='rtsp://camera.invalid/stream1')

                class UnsafeFixture:
                    def __enter__(self):
                        self.container = real_open(str(fixture))
                        self.streams = self.container.streams
                        return self

                    def __exit__(self, *_args):
                        self.container.close()

                    def demux(self, stream):
                        for index, packet in enumerate(self.container.demux(stream)):
                            if not packet.size:
                                yield packet
                                continue
                            if index == 1 or scenario == 'too_many':
                                packet.dts = packet.pts = 0
                            if scenario == 'reordered_pts' and index == 1:
                                packet.pts = 1
                            if scenario == 'wide_gap' and index == 2:
                                packet.dts = packet.pts = int(2 / packet.time_base)
                            if scenario == 'insufficient_ticks' and index == 2:
                                packet.dts = packet.pts = 1
                            yield packet

                def open_fixture(file, *arguments, **options):
                    return UnsafeFixture() if file == source.source else real_open(file, *arguments, **options)

                with patch('av.open', side_effect=open_fixture), redirect_stdout(io.StringIO()):
                    result = record_segment(source, root / 'recorded.mp4', math.inf, threading.Event(), av)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['error_code'], 'timestamp_correction_limit')

    def test_worker_start_failure_still_saves_private_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.make_args(Path(directory))
            sources = validate_inputs(args)
            completed = Future()
            completed.set_result({'camera': 'front', 'status': 'completed', 'segments': []})
            output = io.StringIO()
            with patch('tagad_pipeline.camera_recording.ThreadPoolExecutor') as pool, redirect_stdout(output):
                executor = pool.return_value.__enter__.return_value
                executor.submit.side_effect = [completed, RuntimeError('private-password')]
                self.assertEqual(run(args, sources, object()), 1)
            manifest = next(args.output_root.glob('*/recording-manifest.json'))
            text = manifest.read_text(encoding='utf-8')
            self.assertEqual(json.loads(text)['status'], 'partial')
            self.assertNotIn('private-password', text + output.getvalue())

    def test_synthetic_video_remux_is_playable_after_input_ends(self):
        import av
        import numpy as np

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'synthetic.mp4'
            with av.open(str(original), mode='w') as container:
                stream = container.add_stream('libx264', rate=15)
                stream.width, stream.height, stream.pix_fmt = 64, 64, 'yuv420p'
                for _index in range(15):
                    frame = av.VideoFrame.from_ndarray(np.zeros((64, 64, 3), dtype=np.uint8), format='rgb24')
                    for packet in stream.encode(frame):
                        container.mux(packet)
                for packet in stream.encode():
                    container.mux(packet)
            source = SimpleNamespace(position='front', source='rtsp://user:secret@camera.invalid/stream1')
            real_open = av.open

            def synthetic_open(file, *arguments, **options):
                if file == source.source:
                    return real_open(str(original), mode='r')
                return real_open(file, *arguments, **options)

            destination = root / 'recorded.mp4'
            with patch('av.open', side_effect=synthetic_open), redirect_stdout(io.StringIO()):
                result = record_segment(source, destination, math.inf, threading.Event(), av)
            self.assertEqual(result['error_code'], 'stream_ended')
            self.assertEqual(result['packets'], 15)
            self.assertGreater(result['bytes'], 0)
            self.assertNotIn('secret', json.dumps(result))
            with real_open(str(destination), mode='r') as container:
                self.assertEqual(len(container.streams.audio), 0)
                self.assertEqual(sum(1 for _frame in container.decode(video=0)), 15)


if __name__ == '__main__':
    unittest.main()
