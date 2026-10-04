from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework import serializers


LIFECYCLE_VALUES = {'active', 'archived', 'all'}


def filter_lifecycle(queryset, value):
    value = (value or 'active').strip().lower()
    if value not in LIFECYCLE_VALUES:
        raise serializers.ValidationError({
            'lifecycle': 'Choose active, archived, or all.',
        })
    if value == 'archived':
        return queryset.filter(archived_at__isnull=False)
    if value == 'active':
        return queryset.filter(archived_at__isnull=True)
    return queryset


def archive_record(record, user):
    if record.archived_at is None:
        record.archived_at = timezone.now()
        record.archived_by = user
        record.save(update_fields=['archived_at', 'archived_by'])
        return True
    return False


def restore_record(record):
    if record.archived_at is not None:
        record.archived_at = None
        record.archived_by = None
        record.save(update_fields=['archived_at', 'archived_by'])
        return True
    return False


def invalidate_sessions_for_user_ids(user_ids):
    user_ids = {str(user_id) for user_id in user_ids}
    if not user_ids:
        return
    expired_at = timezone.now()
    session_keys = []
    for session in Session.objects.filter(expire_date__gte=expired_at).iterator():
        if session.get_decoded().get(SESSION_KEY) in user_ids:
            session_keys.append(session.session_key)
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()


def invalidate_user_sessions(user):
    invalidate_sessions_for_user_ids([user.pk])
