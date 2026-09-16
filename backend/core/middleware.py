import logging
import re
from uuid import uuid4

from django.contrib.auth import logout

from .authentication import EmailOrUsernameBackend
from .observability import reset_request_id, set_request_id


request_logger = logging.getLogger('tagad.requests')
safe_request_id = re.compile(r'^[A-Za-z0-9._-]{1,64}$')


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get('X-Request-ID', '')
        request.request_id = supplied if safe_request_id.fullmatch(supplied) else str(uuid4())
        token = set_request_id(request.request_id)
        try:
            response = self.get_response(request)
            response['X-Request-ID'] = request.request_id
            if response.status_code >= 500:
                request_logger.error(
                    'Request failed.',
                    extra={
                        'event': 'request_failed',
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                    },
                )
            return response
        finally:
            reset_request_id(token)


class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.authentication_backend = EmailOrUsernameBackend()

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not self.authentication_backend.user_can_authenticate(request.user)
        ):
            logout(request)
        return self.get_response(request)
