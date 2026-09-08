from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import ClassroomSession, EngagementAlert, EngagementSummary, SlideEvent


CATEGORIES = ('engaged', 'attentive', 'confused', 'bored', 'disengaged')


def summary_payload(summary, alert=None):
    counts = {
        category: getattr(summary, f'{category}_count')
        for category in CATEGORIES
    }
    classified = sum(counts.values())
    return {
        'id': summary.pk,
        'schema_version': summary.schema_version,
        'ingestion_id': str(summary.ingestion_id),
        'pipeline_version': summary.pipeline_version,
        'session_id': summary.event.session_id,
        'slide_event_id': summary.event_id,
        'slide_id': summary.event.slide_id,
        'slide_number': summary.event.slide.slide_number,
        'captured_at': summary.captured_at.isoformat(),
        'counts': counts,
        'total_detected': summary.total_detected,
        'unclassified_count': summary.unclassified_count,
        'average_confidence': float(summary.average_confidence),
        'distribution': {
            category: round(count * 100 / classified, 1) if classified else 0
            for category, count in counts.items()
        },
        'alert': ({
            'id': alert.pk,
            'type': alert.alert_type,
            'message': alert.alert_message,
            'created_at': alert.created_at.isoformat(),
        } if alert else None),
    }


def _is_high_disengagement(summary):
    classified = sum(
        getattr(summary, f'{category}_count') for category in CATEGORIES
    )
    return bool(classified and summary.disengaged_count / classified > 0.5)


@transaction.atomic
def ingest_engagement(validated_data):
    existing = (
        EngagementSummary.objects.select_related('event__session', 'event__slide')
        .filter(ingestion_id=validated_data['ingestion_id'])
        .first()
    )
    if existing:
        return existing, None, False
    session = ClassroomSession.objects.select_for_update().get(
        pk=validated_data['session_id'],
    )
    event = (
        SlideEvent.objects.select_for_update()
        .select_related('slide')
        .get(pk=validated_data['slide_event_id'])
    )
    if event.session_id != session.pk:
        raise ValueError('The slide event does not belong to this session.')
    if session.ended_at:
        raise ValueError('Engagement cannot be submitted to a completed session.')
    if validated_data['captured_at'] < session.started_at:
        raise ValueError('captured_at cannot be earlier than the session start.')
    if validated_data['captured_at'] > timezone.now() + timedelta(seconds=5):
        raise ValueError('captured_at cannot be in the future.')
    current_event = session.slide_events.order_by('-entered_at', '-pk').first()
    if current_event.pk != event.pk:
        raise ValueError('The slide event is no longer active.')

    counts = validated_data['counts']
    summary, created = EngagementSummary.objects.get_or_create(
        ingestion_id=validated_data['ingestion_id'],
        defaults={
            'event': event,
            **{f'{category}_count': counts[category] for category in CATEGORIES},
            'total_detected': validated_data['total_detected'],
            'unclassified_count': validated_data['unclassified_count'],
            'average_confidence': validated_data['average_confidence'],
            'captured_at': validated_data['captured_at'],
            'schema_version': validated_data['schema_version'],
            'pipeline_version': validated_data['pipeline_version'],
        },
    )
    if not created:
        return summary, None, False

    alert = None
    high = _is_high_disengagement(summary)
    if not high and event.disengagement_alert_active:
        event.disengagement_alert_active = False
        event.save(update_fields=['disengagement_alert_active'])
    elif high and not event.disengagement_alert_active:
        required = max(1, settings.ENGAGEMENT_ALERT_CONSECUTIVE_WINDOWS)
        recent = list(event.summaries.order_by('-captured_at', '-pk')[:required])
        if len(recent) == required and all(_is_high_disengagement(item) for item in recent):
            alert = EngagementAlert.objects.create(
                summary=summary,
                alert_type='high_disengagement',
                alert_message=(
                    f'Disengagement exceeded 50% for {required} consecutive monitoring windows.'
                ),
            )
            event.disengagement_alert_active = True
            event.save(update_fields=['disengagement_alert_active'])

    payload = summary_payload(summary, alert)
    transaction.on_commit(lambda: broadcast_engagement(event.session_id, payload))
    return summary, alert, True


def broadcast_engagement(session_id, payload):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f'engagement_session_{session_id}',
            {'type': 'engagement.update', 'payload': payload},
        )
