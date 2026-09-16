import logging

from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .health import run_readiness_checks


logger = logging.getLogger('tagad.health')


@never_cache
@require_GET
def liveness(request):
    return JsonResponse({
        'status': 'ok',
        'request_id': request.request_id,
    })


@never_cache
@require_GET
def readiness(request):
    checks = run_readiness_checks(logger)
    is_ready = all(check['status'] == 'ok' for check in checks.values())
    return JsonResponse({
        'status': 'ready' if is_ready else 'unavailable',
        'request_id': request.request_id,
        'checks': checks,
    }, status=200 if is_ready else 503)

