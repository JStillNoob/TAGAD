import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger('tagad.api')
GENERIC_ERROR = 'Something went wrong. Please try again or contact an administrator.'


def tagad_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and response.status_code < 500:
        return response

    request = context.get('request')
    request_id = getattr(request, 'request_id', '-')
    logger.error(
        'Unexpected API error.',
        extra={
            'event': 'unexpected_api_error',
            'method': getattr(request, 'method', '-'),
            'path': getattr(request, 'path', '-'),
            'exception_type': type(exc).__name__,
            'request_id': request_id,
        },
    )
    return Response({
        'detail': GENERIC_ERROR,
        'request_id': request_id,
    }, status=500)
