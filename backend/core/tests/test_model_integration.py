import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from core.model_integration import (
    ModelConfigurationError,
    build_engagement_payload,
    model_artifact_status,
    require_model_artifacts,
)
from core.engagement_views import EngagementIngestionSerializer


class ModelArtifactConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.yolo = root / 'head.pt'
        self.landmarker = root / 'face.task'
        self.state_model = root / 'state.joblib'
        self.attention_model = root / 'attention.joblib'
        for artifact in (self.yolo, self.landmarker, self.state_model, self.attention_model):
            artifact.write_bytes(b'test artifact')

    def settings(self, **overrides):
        values = {
            'TAGAD_YOLO_MODEL_PATH': str(self.yolo),
            'TAGAD_FACE_LANDMARKER_PATH': str(self.landmarker),
            'TAGAD_STATE_MODEL_PATH': str(self.state_model),
            'TAGAD_ATTENTION_MODEL_PATH': str(self.attention_model),
        }
        values.update(overrides)
        return override_settings(**values)

    def test_all_expected_artifacts_can_be_verified_without_loading_them(self):
        with self.settings():
            statuses = model_artifact_status()
            configured = require_model_artifacts()

        self.assertTrue(all(status.ready for status in statuses))
        self.assertEqual(configured['head_detector'], self.yolo)
        self.assertEqual(configured['face_landmarker'], self.landmarker)
        self.assertEqual(configured['state_classifier'], self.state_model)
        self.assertEqual(configured['attention_classifier'], self.attention_model)

    def test_missing_and_incompatible_artifacts_fail_safely(self):
        missing = self.yolo.with_name('missing.pt')
        with self.settings(TAGAD_YOLO_MODEL_PATH=str(missing)):
            with self.assertRaisesRegex(ModelConfigurationError, 'head_detector'):
                require_model_artifacts()
        with self.settings(TAGAD_FACE_LANDMARKER_PATH=str(self.yolo)):
            statuses = {status.name: status for status in model_artifact_status()}
        self.assertFalse(statuses['face_landmarker'].ready)
        self.assertIn('.task', statuses['face_landmarker'].detail)

        self.state_model.write_bytes(b'')
        with self.settings():
            statuses = {status.name: status for status in model_artifact_status()}
        self.assertFalse(statuses['state_classifier'].ready)
        self.assertEqual(statuses['state_classifier'].detail, 'File is empty.')

    def test_check_command_reports_readiness_and_exits_nonzero_when_incomplete(self):
        output = io.StringIO()
        with self.settings():
            call_command('check_model_setup', stdout=output)
        self.assertIn('[READY] head_detector', output.getvalue())
        self.assertIn('All model artifacts are ready.', output.getvalue())

        with self.settings(TAGAD_ATTENTION_MODEL_PATH=''):
            with self.assertRaises(CommandError):
                call_command('check_model_setup', stdout=io.StringIO(), stderr=io.StringIO())


@override_settings(TAGAD_MODEL_PIPELINE_VERSION='offline-test-1')
class EngagementPayloadAdapterTests(SimpleTestCase):
    def test_predictions_are_aggregated_into_the_stage_one_contract(self):
        captured_at = datetime(2026, 9, 12, 8, 30, tzinfo=timezone.utc)
        payload = build_engagement_payload(
            session_id=12,
            slide_event_id=30,
            captured_at=captured_at,
            predictions=[
                {'label': 'Engaged', 'confidence': 0.9},
                {'label': 'engaged', 'confidence': 0.8},
                {'label': 'confused', 'confidence': 0.7},
                {'label': None},
            ],
        )

        UUID(payload['ingestion_id'])
        self.assertEqual(payload['pipeline_version'], 'offline-test-1')
        self.assertEqual(payload['counts'], {
            'engaged': 2, 'attentive': 0, 'confused': 1, 'bored': 0, 'disengaged': 0,
        })
        self.assertEqual(payload['total_detected'], 4)
        self.assertEqual(payload['unclassified_count'], 1)
        self.assertEqual(payload['average_confidence'], 80.0)
        self.assertEqual(payload['captured_at'], captured_at.isoformat())
        serializer = EngagementIngestionSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_model_outputs_fail_before_reaching_django_ingestion(self):
        with self.assertRaisesRegex(ModelConfigurationError, 'Unsupported engagement label'):
            build_engagement_payload(
                session_id=1, slide_event_id=1,
                predictions=[{'label': 'sleeping', 'confidence': 0.9}],
            )
        with self.assertRaisesRegex(ModelConfigurationError, 'between 0 and 1'):
            build_engagement_payload(
                session_id=1, slide_event_id=1,
                predictions=[{'label': 'engaged', 'confidence': 91}],
            )
        with self.assertRaisesRegex(ModelConfigurationError, 'no detections'):
            build_engagement_payload(session_id=1, slide_event_id=1, predictions=[])
