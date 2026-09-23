import json
from dataclasses import dataclass
from pathlib import Path


POSITIONS = {'front', 'left', 'right'}
SOURCE_TYPES = {'simulated', 'live'}
CAMERA_KEYS = {
    'position', 'source', 'source_type', 'loop',
    'simulate_disconnect_after_frames', 'simulate_disconnect_seconds',
}
ROOT_KEYS = {
    'poll_seconds', 'heartbeat_seconds', 'summary_seconds', 'analysis_hz',
    'reconnect_attempts', 'reconnect_backoff_seconds', 'cameras',
}


class CameraConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class CameraSource:
    position: str
    source: str
    source_type: str
    loop: bool
    available: bool
    simulate_disconnect_after_frames: int = 0
    simulate_disconnect_seconds: float = 1.0


@dataclass(frozen=True)
class ControllerConfiguration:
    cameras: tuple
    poll_seconds: float = 2.0
    heartbeat_seconds: float = 2.0
    summary_seconds: float = 3.0
    analysis_hz: float = 8.0
    reconnect_attempts: int = 3
    reconnect_backoff_seconds: float = 1.0

    def source_for(self, position):
        return next((item for item in self.cameras if item.position == position), None)


def _positive_number(data, name, default):
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise CameraConfigurationError(f'{name} must be greater than zero.')
    return float(value)


def load_configuration(path):
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise CameraConfigurationError('The local camera configuration could not be read.') from error
    if not isinstance(data, dict):
        raise CameraConfigurationError('The camera configuration must be a JSON object.')
    unknown = set(data) - ROOT_KEYS
    if unknown:
        raise CameraConfigurationError(f'Unknown controller option: {sorted(unknown)[0]}.')
    raw_cameras = data.get('cameras')
    if not isinstance(raw_cameras, list) or not raw_cameras:
        raise CameraConfigurationError('At least one camera must be configured.')

    cameras = []
    positions = set()
    for raw in raw_cameras:
        if not isinstance(raw, dict):
            raise CameraConfigurationError('Each camera configuration must be an object.')
        unknown = set(raw) - CAMERA_KEYS
        if unknown:
            raise CameraConfigurationError(f'Unknown camera option: {sorted(unknown)[0]}.')
        position = str(raw.get('position', '')).strip().lower()
        if position not in POSITIONS:
            raise CameraConfigurationError('Camera position must be front, left, or right.')
        if position in positions:
            raise CameraConfigurationError(f'Duplicate {position} camera configuration.')
        positions.add(position)
        source_type = str(raw.get('source_type', '')).strip().lower()
        if source_type not in SOURCE_TYPES:
            raise CameraConfigurationError(f'{position} camera has an invalid source type.')
        source = raw.get('source')
        if not isinstance(source, (str, int)) or str(source).strip() == '':
            raise CameraConfigurationError(f'{position} camera requires a source.')
        source = str(source).strip()
        available = True
        if source_type == 'simulated':
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = path.parent / source_path
            source = str(source_path.resolve())
            available = Path(source).is_file()
        loop = raw.get('loop', source_type == 'simulated')
        if not isinstance(loop, bool):
            raise CameraConfigurationError(f'{position} camera loop must be true or false.')
        disconnect_after = raw.get('simulate_disconnect_after_frames', 0)
        if isinstance(disconnect_after, bool) or not isinstance(disconnect_after, int):
            raise CameraConfigurationError(
                f'{position} camera simulate_disconnect_after_frames must be an integer.',
            )
        if disconnect_after < 0:
            raise CameraConfigurationError(
                f'{position} camera simulate_disconnect_after_frames cannot be negative.',
            )
        disconnect_seconds = raw.get('simulate_disconnect_seconds', 1)
        if (
            isinstance(disconnect_seconds, bool)
            or not isinstance(disconnect_seconds, (int, float))
            or disconnect_seconds < 0
        ):
            raise CameraConfigurationError(
                f'{position} camera simulate_disconnect_seconds cannot be negative.',
            )
        cameras.append(CameraSource(
            position, source, source_type, loop, available,
            disconnect_after, float(disconnect_seconds),
        ))

    reconnect_attempts = data.get('reconnect_attempts', 3)
    if isinstance(reconnect_attempts, bool) or not isinstance(reconnect_attempts, int):
        raise CameraConfigurationError('reconnect_attempts must be an integer.')
    if reconnect_attempts < 1:
        raise CameraConfigurationError('reconnect_attempts must be at least one.')
    return ControllerConfiguration(
        cameras=tuple(cameras),
        poll_seconds=_positive_number(data, 'poll_seconds', 2),
        heartbeat_seconds=_positive_number(data, 'heartbeat_seconds', 2),
        summary_seconds=_positive_number(data, 'summary_seconds', 3),
        analysis_hz=_positive_number(data, 'analysis_hz', 8),
        reconnect_attempts=reconnect_attempts,
        reconnect_backoff_seconds=_positive_number(data, 'reconnect_backoff_seconds', 1),
    )
