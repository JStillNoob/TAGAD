import json
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from logging import Formatter, Filter


_request_id = ContextVar('request_id', default='-')
_sensitive_value = re.compile(
    r'(?i)\b([A-Za-z0-9_-]*(?:password|secret|token|api[_-]?key|authorization|cookie)[A-Za-z0-9_-]*)'
    r'(\s*[:=]\s*)(?:"[^"]*"|\'[^\']*\'|[^\s,;]+)',
)


def set_request_id(value):
    return _request_id.set(value)


def reset_request_id(token):
    _request_id.reset(token)


def current_request_id():
    return _request_id.get()


def redact(value):
    return _sensitive_value.sub(r'\1\2[REDACTED]', str(value))


class RequestContextFilter(Filter):
    def filter(self, record):
        if not getattr(record, 'request_id', None):
            record.request_id = current_request_id()
        return True


class SafeJsonFormatter(Formatter):
    def format(self, record):
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': redact(record.getMessage()),
            'request_id': getattr(record, 'request_id', '-'),
        }
        for field in ('event', 'method', 'path', 'status_code', 'component', 'exception_type'):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value if isinstance(value, (int, float, bool)) else redact(value)
        return json.dumps(payload, ensure_ascii=True)
