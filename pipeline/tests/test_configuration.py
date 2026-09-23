import json
import tempfile
import unittest
from pathlib import Path

from tagad_pipeline.configuration import CameraConfigurationError, load_configuration


class CameraConfigurationTests(unittest.TestCase):
    def write_config(self, directory, data):
        path = Path(directory) / 'camera_sources.local.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_loads_positions_and_marks_a_missing_source_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'center.mp4').write_bytes(b'video')
            path = self.write_config(directory, {
                'cameras': [
                    {
                        'position': 'front', 'source': 'center.mp4',
                        'source_type': 'simulated', 'loop': True,
                    },
                    {
                        'position': 'left', 'source': 'missing.mp4',
                        'source_type': 'simulated', 'loop': True,
                    },
                ],
            })

            configuration = load_configuration(path)

            self.assertTrue(configuration.source_for('front').available)
            self.assertFalse(configuration.source_for('left').available)
            self.assertIsNone(configuration.source_for('right'))

    def test_rejects_duplicate_positions_and_unknown_options(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate = self.write_config(directory, {'cameras': [
                {'position': 'front', 'source': 'one.mp4', 'source_type': 'simulated'},
                {'position': 'front', 'source': 'two.mp4', 'source_type': 'simulated'},
            ]})
            with self.assertRaisesRegex(CameraConfigurationError, 'Duplicate front'):
                load_configuration(duplicate)

            unknown = self.write_config(directory, {
                'secret_path': 'must-not-be-accepted',
                'cameras': [
                    {'position': 'front', 'source': 'one.mp4', 'source_type': 'simulated'},
                ],
            })
            with self.assertRaisesRegex(CameraConfigurationError, 'Unknown controller option'):
                load_configuration(unknown)

    def test_errors_identify_position_without_exposing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            private_source = 'rtsp://user:password@camera/stream'
            path = self.write_config(directory, {'cameras': [{
                'position': 'left', 'source': private_source,
                'source_type': 'bad-type',
            }]})
            with self.assertRaises(CameraConfigurationError) as raised:
                load_configuration(path)
            self.assertIn('left', str(raised.exception))
            self.assertNotIn(private_source, str(raised.exception))


if __name__ == '__main__':
    unittest.main()
