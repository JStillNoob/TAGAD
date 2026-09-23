from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from django.conf import settings


ENGAGEMENT_LABELS = ('engaged', 'attentive', 'confused', 'bored', 'disengaged')
STATE_FEATURE_ORDER = (
    'mean_pitch', 'mean_yaw', 'mean_roll', 'mean_Gh', 'mean_Gv',
    'bs_eyeBlinkLeft', 'bs_eyeBlinkRight', 'bs_eyeSquintLeft', 'bs_eyeSquintRight',
    'bs_eyeWideLeft', 'bs_eyeWideRight', 'bs_browDownLeft', 'bs_browDownRight',
    'bs_browInnerUp', 'bs_browOuterUpLeft', 'bs_browOuterUpRight',
    'bs_cheekSquintLeft', 'bs_cheekSquintRight', 'bs_jawOpen',
    'bs_mouthFrownLeft', 'bs_mouthFrownRight', 'bs_mouthSmileLeft',
    'bs_mouthSmileRight', 'bs_mouthPressLeft', 'bs_mouthPressRight',
)
ATTENTION_FEATURE_ORDER = (
    'mean_pitch', 'mean_yaw', 'mean_roll', 'mean_Gh', 'mean_Gv',
    'std_pitch', 'std_yaw', 'std_roll', 'std_Gh', 'std_Gv',
)

ARTIFACT_SETTINGS = {
    'head_detector': ('TAGAD_YOLO_MODEL_PATH', {'.pt'}),
    'face_landmarker': ('TAGAD_FACE_LANDMARKER_PATH', {'.task'}),
    'state_classifier': ('TAGAD_STATE_MODEL_PATH', {'.joblib', '.pkl'}),
    'attention_classifier': ('TAGAD_ATTENTION_MODEL_PATH', {'.joblib', '.pkl'}),
}


class ModelConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactStatus:
    name: str
    configured: bool
    ready: bool
    path: str
    detail: str


def _artifact_path(raw_path):
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else settings.BASE_DIR / path


def model_artifact_status():
    statuses = []
    for name, (setting_name, extensions) in ARTIFACT_SETTINGS.items():
        raw_path = str(getattr(settings, setting_name, '')).strip()
        if not raw_path:
            statuses.append(ArtifactStatus(name, False, False, '', 'Path is not configured.'))
            continue

        path = _artifact_path(raw_path)
        if path.suffix.lower() not in extensions:
            allowed = ', '.join(sorted(extensions))
            statuses.append(ArtifactStatus(
                name, True, False, str(path), f'Expected one of these file types: {allowed}.',
            ))
        elif not path.is_file():
            statuses.append(ArtifactStatus(name, True, False, str(path), 'File was not found.'))
        elif path.stat().st_size == 0:
            statuses.append(ArtifactStatus(name, True, False, str(path), 'File is empty.'))
        else:
            statuses.append(ArtifactStatus(name, True, True, str(path), 'Ready.'))
    return statuses


def require_model_artifacts():
    statuses = model_artifact_status()
    failures = [status for status in statuses if not status.ready]
    if failures:
        summary = '; '.join(f'{status.name}: {status.detail}' for status in failures)
        raise ModelConfigurationError(summary)
    return {status.name: Path(status.path) for status in statuses}


def build_engagement_payload(
    *, session_id, slide_event_id, predictions, captured_at=None,
    pipeline_version=None, ingestion_id=None,
):
    counts = {label: 0 for label in ENGAGEMENT_LABELS}
    confidences = []
    unclassified_count = 0
    predictions = list(predictions)
    if not predictions:
        raise ModelConfigurationError('Do not submit an engagement window with no detections.')

    for prediction in predictions:
        label = prediction.get('label')
        if label is None:
            unclassified_count += 1
            continue
        normalized_label = str(label).strip().lower()
        if normalized_label not in counts:
            raise ModelConfigurationError(f'Unsupported engagement label: {label}.')
        try:
            confidence = float(prediction['confidence'])
        except (KeyError, TypeError, ValueError) as error:
            raise ModelConfigurationError('Every classified prediction needs a numeric confidence.') from error
        if not 0 <= confidence <= 1:
            raise ModelConfigurationError('Prediction confidence must be between 0 and 1.')
        counts[normalized_label] += 1
        confidences.append(confidence)

    captured_at = captured_at or datetime.now(timezone.utc)
    if captured_at.tzinfo is None:
        raise ModelConfigurationError('captured_at must include a timezone.')

    return {
        'schema_version': 1,
        'ingestion_id': str(ingestion_id or uuid4()),
        'pipeline_version': pipeline_version or settings.TAGAD_MODEL_PIPELINE_VERSION,
        'session_id': session_id,
        'slide_event_id': slide_event_id,
        'captured_at': captured_at.isoformat(),
        'counts': counts,
        'total_detected': len(predictions),
        'unclassified_count': unclassified_count,
        'average_confidence': round(
            100 * sum(confidences) / len(confidences), 2,
        ) if confidences else 0,
    }
