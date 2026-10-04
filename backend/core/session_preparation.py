from datetime import timedelta

from django.utils import timezone

from .models import ClassroomSession


PREPARATION_TIMEOUT = timedelta(minutes=30)


def expire_prepared_sessions(*, user=None):
    sessions = ClassroomSession.objects.filter(
        started_at__isnull=True,
        ended_at__isnull=True,
        prepared_at__lt=timezone.now() - PREPARATION_TIMEOUT,
    )
    if user is not None:
        sessions = sessions.filter(user=user)
    return sessions.delete()[0]
