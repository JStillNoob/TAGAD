import hashlib
import hmac
import logging
import math
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from .models import SystemLog, User
from .request_metadata import request_ip


security_logger = logging.getLogger('tagad.security')
KEY_PREFIX = 'tagad-auth-throttle:v1'


@dataclass(frozen=True)
class ThrottleState:
    retry_after: int = 0
    newly_limited: bool = False

    @property
    def limited(self):
        return self.retry_after > 0


def _normalize(value):
    return str(value or '').strip().casefold()


def _fingerprint(value):
    return hmac.new(
        settings.SECRET_KEY.encode(),
        _normalize(value).encode(),
        hashlib.sha256,
    ).hexdigest()


def _scope_key(scope, value):
    return f'{KEY_PREFIX}:{scope}:{_fingerprint(value)}'


def _counter_key(scope, value):
    return f'{_scope_key(scope, value)}:count'


def _block_key(scope, value):
    return f'{_scope_key(scope, value)}:blocked'


def _remaining_block(scope, value):
    key = _block_key(scope, value)
    blocked_until = cache.get(key)
    if not blocked_until:
        return 0
    remaining = math.ceil(float(blocked_until) - time.time())
    if remaining <= 0:
        cache.delete(key)
        return 0
    return remaining


def _increment(scope, value, limit, window_seconds, block_seconds):
    counter_key = _counter_key(scope, value)
    if cache.add(counter_key, 1, timeout=window_seconds):
        count = 1
    else:
        try:
            count = cache.incr(counter_key)
        except ValueError:
            cache.set(counter_key, 1, timeout=window_seconds)
            count = 1

    if count < limit:
        return ThrottleState()

    retry_after = block_seconds
    cache.set(
        _block_key(scope, value),
        time.time() + retry_after,
        timeout=retry_after,
    )
    return ThrottleState(retry_after=retry_after, newly_limited=count == limit)


def _maximum_remaining(scopes):
    return max((_remaining_block(scope, value) for scope, value in scopes), default=0)


def login_throttle_state(identity, client_ip):
    pair = f'{_normalize(identity)}\0{client_ip}'
    retry_after = _maximum_remaining((
        ('login-pair', pair),
        ('login-client', client_ip),
    ))
    return ThrottleState(retry_after=retry_after)


def record_login_failure(identity, client_ip):
    pair = f'{_normalize(identity)}\0{client_ip}'
    states = (
        _increment(
            'login-pair', pair,
            settings.LOGIN_THROTTLE_MAX_FAILURES,
            settings.LOGIN_THROTTLE_WINDOW_SECONDS,
            settings.LOGIN_THROTTLE_BLOCK_SECONDS,
        ),
        _increment(
            'login-client', client_ip,
            settings.LOGIN_THROTTLE_CLIENT_MAX_FAILURES,
            settings.LOGIN_THROTTLE_WINDOW_SECONDS,
            settings.LOGIN_THROTTLE_BLOCK_SECONDS,
        ),
    )
    return ThrottleState(
        retry_after=max(state.retry_after for state in states),
        newly_limited=any(state.newly_limited for state in states),
    )


def clear_login_failures(identity, client_ip):
    pair = f'{_normalize(identity)}\0{client_ip}'
    cache.delete_many((
        _counter_key('login-pair', pair),
        _block_key('login-pair', pair),
    ))


def password_reset_throttle_state(email, client_ip):
    pair = f'{_normalize(email)}\0{client_ip}'
    retry_after = _maximum_remaining((
        ('password-reset-pair', pair),
        ('password-reset-client', client_ip),
    ))
    return ThrottleState(retry_after=retry_after)


def record_password_reset_request(email, client_ip):
    pair = f'{_normalize(email)}\0{client_ip}'
    states = (
        _increment(
            'password-reset-pair', pair,
            settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS,
            settings.PASSWORD_RESET_THROTTLE_WINDOW_SECONDS,
            settings.PASSWORD_RESET_THROTTLE_BLOCK_SECONDS,
        ),
        _increment(
            'password-reset-client', client_ip,
            settings.PASSWORD_RESET_THROTTLE_CLIENT_MAX_REQUESTS,
            settings.PASSWORD_RESET_THROTTLE_WINDOW_SECONDS,
            settings.PASSWORD_RESET_THROTTLE_BLOCK_SECONDS,
        ),
    )
    return ThrottleState(
        retry_after=max(state.retry_after for state in states),
        newly_limited=any(state.newly_limited for state in states),
    )


def record_security_throttle(request, identity, activity, event):
    user = User.objects.filter(
        Q(username__iexact=_normalize(identity))
        | Q(email__iexact=_normalize(identity)),
    ).first()
    client_ip = request_ip(request)
    if user:
        SystemLog.objects.create(
            user=user,
            activity=activity,
            ip_address=client_ip,
        )
    security_logger.warning(
        '%s client=%s account=%s',
        event,
        client_ip or 'unknown',
        user.pk if user else 'unknown',
    )


def throttle_message(action, retry_after):
    minutes = max(1, math.ceil(retry_after / 60))
    return f'Too many {action}. Try again in {minutes} minute{"s" if minutes != 1 else ""}.'

