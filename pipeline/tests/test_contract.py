import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from tagad_pipeline.artifacts import ArtifactVerificationError, sha256, verify_artifacts
from tagad_pipeline.backend_client import BackendClient, build_payload
from tagad_pipeline.benchmark import percentile
from tagad_pipeline.constants import ATTENTION_FEATURES, STATE_FEATURES, combine_state


class StateMappingTests(unittest.TestCase):
    def test_hierarchical_mapping(self):
        self.assertEqual(combine_state('Engaged', 'HigherAttention'), 'Engaged')
        self.assertEqual(combine_state('Engaged', 'LowerAttention'), 'Attentive')
        self.assertEqual(combine_state('Engaged', None), 'Engaged')
        self.assertEqual(combine_state('Confused', None), 'Confused')
        self.assertEqual(combine_state('Bored', None), 'Bored')
        self.assertEqual(combine_state('Drowsy', None), 'Disengaged')
        self.assertEqual(combine_state('LookingAway', None), 'Disengaged')
        self.assertIsNone(combine_state('Unexpected', None))


class PayloadTests(unittest.TestCase):
    def test_builds_backend_schema_with_explicit_unclassified_count(self):
        payload = build_payload(
            session_id=7,
            slide_event_id=11,
            pipeline_version='test-1',
            predictions=[
                {'label': 'Engaged', 'confidence': 0.9},
                {'label': 'Attentive', 'confidence': 0.7},
                {'label': None, 'confidence': None},
            ],
        )
        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['total_detected'], 3)
        self.assertEqual(payload['unclassified_count'], 1)
        self.assertEqual(payload['counts']['engaged'], 1)
        self.assertEqual(payload['counts']['attentive'], 1)
        self.assertEqual(payload['average_confidence'], 80.0)

    def test_rejects_empty_or_unknown_predictions(self):
        with self.assertRaises(ValueError):
            build_payload(
                session_id=1, slide_event_id=1, pipeline_version='test', predictions=[],
            )

    def test_camera_attribution_uses_schema_two(self):
        payload = build_payload(
            session_id=7,
            slide_event_id=11,
            camera_id=23,
            pipeline_version='controller-1',
            predictions=[{'label': 'Engaged', 'confidence': 0.9}],
        )
        self.assertEqual(payload['schema_version'], 2)
        self.assertEqual(payload['camera_id'], 23)
        with self.assertRaises(ValueError):
            build_payload(
                session_id=1,
                slide_event_id=1,
                pipeline_version='test',
                predictions=[{'label': 'Unknown', 'confidence': 0.5}],
            )


class BackendClientTests(unittest.TestCase):
    @patch('tagad_pipeline.backend_client.urlopen')
    def test_context_request_uses_private_header_and_expected_endpoint(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"active": true}'
        urlopen.return_value = response

        result = BackendClient('http://127.0.0.1:8000/', 'private-key').session_context(9)

        self.assertTrue(result['active'])
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            'http://127.0.0.1:8000/api/auth/pipeline/sessions/9/context/',
        )
        self.assertEqual(request.get_header('X-pipeline-key'), 'private-key')

    @patch('tagad_pipeline.backend_client.urlopen')
    def test_work_and_heartbeat_use_private_orchestration_endpoints(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true}'
        urlopen.return_value = response
        client = BackendClient('http://127.0.0.1:8000', 'private-key')

        client.work()
        work_request = urlopen.call_args.args[0]
        self.assertEqual(work_request.full_url, 'http://127.0.0.1:8000/api/auth/pipeline/work/')
        self.assertEqual(work_request.method, 'GET')

        client.heartbeat({'camera_id': 1})
        heartbeat_request = urlopen.call_args.args[0]
        self.assertEqual(
            heartbeat_request.full_url,
            'http://127.0.0.1:8000/api/auth/pipeline/cameras/heartbeat/',
        )
        self.assertEqual(heartbeat_request.method, 'POST')

    @patch('tagad_pipeline.backend_client.time.sleep')
    @patch('tagad_pipeline.backend_client.urlopen')
    def test_temporary_network_failure_retries_the_same_request(self, urlopen, sleep):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"stored": true}'
        urlopen.side_effect = [URLError('temporary'), response]
        client = BackendClient('http://127.0.0.1:8000', 'private-key', retries=1)

        result = client.submit({'ingestion_id': 'same-id'})

        self.assertTrue(result['stored'])
        self.assertEqual(urlopen.call_count, 2)
        self.assertIs(urlopen.call_args_list[0].args[0], urlopen.call_args_list[1].args[0])
        sleep.assert_called_once()


class ArtifactTests(unittest.TestCase):
    def test_frozen_manifest_matches_the_code_feature_contract(self):
        manifest_path = Path(__file__).resolve().parents[1] / 'artifact-manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        self.assertEqual(tuple(manifest['state_features']), STATE_FEATURES)
        self.assertEqual(tuple(manifest['attention_features']), ATTENTION_FEATURES)

    def test_verifies_size_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / 'model.bin'
            artifact.write_bytes(b'tagad-model')
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'artifacts': [{
                    'file': artifact.name,
                    'bytes': artifact.stat().st_size,
                    'sha256': sha256(artifact),
                }],
            }), encoding='utf-8')

            verify_artifacts(root, manifest)
            artifact.write_bytes(b'changed')
            with self.assertRaises(ArtifactVerificationError):
                verify_artifacts(root, manifest)


class BenchmarkTests(unittest.TestCase):
    def test_percentile_uses_the_nearest_rank(self):
        self.assertEqual(percentile([], 0.95), 0.0)
        self.assertEqual(percentile([0.4, 0.1, 0.3, 0.2], 0.95), 0.4)


if __name__ == '__main__':
    unittest.main()
