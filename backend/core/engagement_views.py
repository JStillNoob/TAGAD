import hmac
import random
from uuid import uuid4

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .engagement_pipeline import CATEGORIES, ingest_engagement, summary_payload
from .models import ClassroomSession, SlideEvent
from .session_access import sessions_for_user


class EngagementCountsSerializer(serializers.Serializer):
    engaged = serializers.IntegerField(min_value=0)
    attentive = serializers.IntegerField(min_value=0)
    confused = serializers.IntegerField(min_value=0)
    bored = serializers.IntegerField(min_value=0)
    disengaged = serializers.IntegerField(min_value=0)


class EngagementIngestionSerializer(serializers.Serializer):
    schema_version = serializers.IntegerField(min_value=1, max_value=1)
    ingestion_id = serializers.UUIDField()
    pipeline_version = serializers.CharField(max_length=50)
    session_id = serializers.IntegerField(min_value=1)
    slide_event_id = serializers.IntegerField(min_value=1)
    captured_at = serializers.DateTimeField()
    counts = EngagementCountsSerializer()
    total_detected = serializers.IntegerField(min_value=1)
    unclassified_count = serializers.IntegerField(min_value=0)
    average_confidence = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100,
    )

    def validate(self, attrs):
        classified = sum(attrs['counts'][category] for category in CATEGORIES)
        if classified + attrs['unclassified_count'] != attrs['total_detected']:
            raise serializers.ValidationError({
                'total_detected': 'Must equal classified counts plus unclassified_count.',
            })
        return attrs


def _ingest_response(serializer):
    try:
        summary, alert, created = ingest_engagement(serializer.validated_data)
    except (ClassroomSession.DoesNotExist, SlideEvent.DoesNotExist):
        raise serializers.ValidationError({'detail': 'Session or slide event was not found.'})
    except ValueError as error:
        raise serializers.ValidationError({'detail': str(error)})
    return Response(
        summary_payload(summary, alert),
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


class EngagementIngestionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        expected = settings.PIPELINE_API_KEY
        supplied = request.headers.get('X-Pipeline-Key', '')
        if not expected:
            return Response(
                {'detail': 'Pipeline ingestion is not configured.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not hmac.compare_digest(supplied, expected):
            return Response({'detail': 'Invalid pipeline credential.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = EngagementIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _ingest_response(serializer)


class EngagementSimulatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not settings.DEBUG or not settings.ENABLE_PIPELINE_SIMULATOR:
            return Response({'detail': 'The engagement simulator is disabled.'}, status=status.HTTP_404_NOT_FOUND)
        session = get_object_or_404(
            sessions_for_user(request.user).filter(user=request.user, ended_at__isnull=True),
            pk=pk,
        )
        event = session.slide_events.order_by('-entered_at', '-pk').first()
        if event is None:
            raise serializers.ValidationError({'detail': 'Enter a presentation slide first.'})

        sequence = event.summaries.filter(pipeline_version='simulator-1').count() % 8
        if sequence in (4, 5, 6):
            counts = {'engaged': 3, 'attentive': 3, 'confused': 2, 'bored': 3, 'disengaged': 19}
        else:
            engaged = random.randint(14, 19)
            counts = {
                'engaged': engaged,
                'attentive': 22 - engaged,
                'confused': 3,
                'bored': 2,
                'disengaged': 3,
            }
        payload = {
            'schema_version': 1,
            'ingestion_id': uuid4(),
            'pipeline_version': 'simulator-1',
            'session_id': session.pk,
            'slide_event_id': event.pk,
            'captured_at': timezone.now(),
            'counts': counts,
            'total_detected': 32,
            'unclassified_count': 2,
            'average_confidence': '86.00',
        }
        serializer = EngagementIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return _ingest_response(serializer)
