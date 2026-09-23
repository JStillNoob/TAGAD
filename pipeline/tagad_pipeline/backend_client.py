import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .constants import FINAL_LABELS


class BackendRequestError(RuntimeError):
    pass


def build_payload(
    *, session_id, slide_event_id, predictions, pipeline_version, camera_id=None,
):
    predictions = list(predictions)
    if not predictions:
        raise ValueError('Cannot submit an empty engagement window.')

    counts = {label.lower(): 0 for label in FINAL_LABELS}
    confidences = []
    unclassified = 0
    for prediction in predictions:
        label = prediction.get('label')
        if label is None:
            unclassified += 1
            continue
        normalized = str(label).strip().lower()
        if normalized not in counts:
            raise ValueError(f'Unsupported engagement label: {label}.')
        confidence = float(prediction['confidence'])
        if not 0 <= confidence <= 1:
            raise ValueError('Prediction confidence must be between 0 and 1.')
        counts[normalized] += 1
        confidences.append(confidence)

    payload = {
        'schema_version': 2 if camera_id is not None else 1,
        'ingestion_id': str(uuid4()),
        'pipeline_version': pipeline_version,
        'session_id': session_id,
        'slide_event_id': slide_event_id,
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'counts': counts,
        'total_detected': len(predictions),
        'unclassified_count': unclassified,
        'average_confidence': round(
            100 * sum(confidences) / len(confidences), 2,
        ) if confidences else 0,
    }
    if camera_id is not None:
        payload['camera_id'] = camera_id
    return payload


class BackendClient:
    def __init__(self, base_url, api_key, *, timeout=10, retries=2):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries

    def session_context(self, session_id):
        return self._request(
            'GET', f'/api/auth/pipeline/sessions/{session_id}/context/',
        )

    def work(self):
        return self._request('GET', '/api/auth/pipeline/work/')

    def heartbeat(self, payload):
        return self._request('POST', '/api/auth/pipeline/cameras/heartbeat/', payload)

    def submit(self, payload):
        return self._request('POST', '/api/auth/pipeline/engagement/', payload)

    def _request(self, method, path, payload=None):
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(
            f'{self.base_url}{path}',
            data=body,
            method=method,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Pipeline-Key': self.api_key,
            },
        )
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode('utf-8'))
            except HTTPError as error:
                detail = error.read().decode('utf-8', errors='replace')
                if error.code < 500 or attempt == self.retries:
                    raise BackendRequestError(
                        f'Backend returned HTTP {error.code}: {detail}',
                    ) from error
                last_error = error
            except URLError as error:
                last_error = error
                if attempt == self.retries:
                    break
            time.sleep(0.5 * (attempt + 1))
        raise BackendRequestError(f'Could not reach the backend: {last_error}') from last_error
