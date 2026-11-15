from datetime import timedelta

from django.utils import timezone
from django.http import Http404

from .models import ClassroomSession
from .session_lifecycle import cancel_preparation, locked_meeting


PREPARATION_TIMEOUT = timedelta(minutes=30)


def expire_prepared_sessions(*, user=None):
    sessions = ClassroomSession.objects.filter(
        started_at__isnull=True,
        ended_at__isnull=True,
        prepared_at__lt=timezone.now() - PREPARATION_TIMEOUT,
    )
    if user is not None:
        sessions = sessions.filter(user=user)
    cutoff = timezone.now() - PREPARATION_TIMEOUT
    deleted = 0
    for session_id in sessions.values_list('pk', flat=True):
        try:
            with locked_meeting(session_id) as session:
                if session.started_at is None and session.ended_at is None and session.prepared_at < cutoff:
                    deleted += cancel_preparation(session)
        except Http404:
            continue
    return deleted
