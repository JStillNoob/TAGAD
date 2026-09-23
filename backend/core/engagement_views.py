import hmac
import random
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .engagement_pipeline import CATEGORIES, ingest_engagement, summary_payload
from .models import Camera, CameraWorkerStatus, ClassroomSession, SessionCamera, SlideEvent
from .session_access import sessions_for_user


class EngagementCountsSerializer(serializers.Serializer):
    engaged = serializers.IntegerField(min_value=0)
    attentive = serializers.IntegerField(min_value=0)
    confused = serializers.IntegerField(min_value=0)
    bored = serializers.IntegerField(min_value=0)
    disengaged = serializers.IntegerField(min_value=0)


class EngagementIngestionSerializer(serializers.Serializer):
    schema_version = serializers.IntegerField(min_value=1, max_value=2)
    ingestion_id = serializers.UUIDField()
    pipeline_version = serializers.CharField(max_length=50)
    session_id = serializers.IntegerField(min_value=1)
    slide_event_id = serializers.IntegerField(min_value=1)
    camera_id = serializers.IntegerField(min_value=1, required=False)
    captured_at = serializers.DateTimeField()
    counts = EngagementCountsSerializer()
    total_detected = serializers.IntegerField(min_value=1)
    unclassified_count = serializers.IntegerField(min_value=0)
    average_confidence = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100,
    )

    def validate(self, attrs):
        if attrs['schema_version'] == 2 and not attrs.get('camera_id'):
            raise serializers.ValidationError({
                'camera_id': 'Schema version 2 requires a camera ID.',
            })
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


def _pipeline_key_is_valid(request):
    expected = settings.PIPELINE_API_KEY
    supplied = request.headers.get('X-Pipeline-Key', '')
    return bool(expected and hmac.compare_digest(supplied, expected))


def _pipeline_auth_error(request):
    if not settings.PIPELINE_API_KEY:
        return Response(
            {'detail': 'Pipeline ingestion is not configured.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if not _pipeline_key_is_valid(request):
        return Response(
            {'detail': 'Invalid pipeline credential.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


WORKER_STATE_TRANSITIONS = {
    CameraWorkerStatus.State.STARTING: {
        CameraWorkerStatus.State.STARTING,
        CameraWorkerStatus.State.ONLINE,
        CameraWorkerStatus.State.RECONNECTING,
        CameraWorkerStatus.State.OFFLINE,
        CameraWorkerStatus.State.STOPPED,
    },
    CameraWorkerStatus.State.ONLINE: {
        CameraWorkerStatus.State.ONLINE,
        CameraWorkerStatus.State.RECONNECTING,
        CameraWorkerStatus.State.OFFLINE,
        CameraWorkerStatus.State.STOPPED,
    },
    CameraWorkerStatus.State.RECONNECTING: {
        CameraWorkerStatus.State.RECONNECTING,
        CameraWorkerStatus.State.ONLINE,
        CameraWorkerStatus.State.OFFLINE,
        CameraWorkerStatus.State.STOPPED,
    },
    CameraWorkerStatus.State.OFFLINE: {
        CameraWorkerStatus.State.OFFLINE,
        CameraWorkerStatus.State.STARTING,
        CameraWorkerStatus.State.RECONNECTING,
        CameraWorkerStatus.State.STOPPED,
    },
    CameraWorkerStatus.State.STOPPED: {
        CameraWorkerStatus.State.STOPPED,
        CameraWorkerStatus.State.STARTING,
    },
}


class CameraWorkerHeartbeatSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(min_value=1)
    camera_id = serializers.IntegerField(min_value=1)
    state = serializers.ChoiceField(choices=CameraWorkerStatus.State.choices)
    source_type = serializers.ChoiceField(choices=CameraWorkerStatus.SourceType.choices)
    reason = serializers.ChoiceField(
        choices=CameraWorkerStatus.Reason.choices,
        required=False,
        allow_blank=True,
        default='',
    )
    pipeline_version = serializers.CharField(max_length=50)
    analysis_rate = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=0, default=0,
    )
    yolo_candidates = serializers.IntegerField(min_value=0, default=0)
    valid_faces = serializers.IntegerField(min_value=0, default=0)
    confirmed_students = serializers.IntegerField(min_value=0, default=0)
    unclassified_students = serializers.IntegerField(min_value=0, default=0)
    counts = EngagementCountsSerializer(required=False, default=lambda: {
        category: 0 for category in CATEGORIES
    })

    def validate(self, attrs):
        classified = sum(attrs['counts'][category] for category in CATEGORIES)
        if classified + attrs['unclassified_students'] != attrs['confirmed_students']:
            raise serializers.ValidationError({
                'confirmed_students': (
                    'Must equal classified counts plus unclassified_students.'
                ),
            })
        if attrs['valid_faces'] > attrs['yolo_candidates']:
            raise serializers.ValidationError({
                'valid_faces': 'Cannot exceed yolo_candidates.',
            })
        return attrs


def _camera_runtime_payload(link, record, *, now=None):
    now = now or timezone.now()
    timeout = max(1, settings.PIPELINE_HEARTBEAT_TIMEOUT_SECONDS)
    stale = bool(
        record
        and record.state != CameraWorkerStatus.State.STOPPED
        and record.last_heartbeat < now - timedelta(seconds=timeout)
    )
    state_value = CameraWorkerStatus.State.OFFLINE if stale else (
        record.state if record else CameraWorkerStatus.State.STOPPED
    )
    reason = CameraWorkerStatus.Reason.HEARTBEAT_STALE if stale else (
        record.reason if record else ''
    )
    counts = record.latest_counts if record else {category: 0 for category in CATEGORIES}
    return {
        'camera_id': link.camera_id,
        'name': link.camera.camera_name,
        'position': link.camera.position,
        'position_label': link.camera.get_position_display(),
        'official_analytics': link.camera.position == Camera.Position.FRONT,
        'state': state_value,
        'state_label': CameraWorkerStatus.State(state_value).label,
        'source_type': record.source_type if record else None,
        'source_label': record.get_source_type_display() if record else None,
        'reason': reason,
        'last_heartbeat': record.last_heartbeat.isoformat() if record else None,
        'pipeline_version': record.pipeline_version if record else None,
        'analysis_rate': float(record.analysis_rate) if record else 0,
        'yolo_candidates': record.yolo_candidates if record else 0,
        'valid_faces': record.valid_faces if record else 0,
        'confirmed_students': record.confirmed_students if record else 0,
        'unclassified_students': record.unclassified_students if record else 0,
        'counts': counts,
    }


class EngagementIngestionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        auth_error = _pipeline_auth_error(request)
        if auth_error:
            return auth_error
        serializer = EngagementIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _ingest_response(serializer)


class PipelineSessionContextView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk):
        auth_error = _pipeline_auth_error(request)
        if auth_error:
            return auth_error

        session = get_object_or_404(
            ClassroomSession.objects.prefetch_related('session_cameras__camera'),
            pk=pk,
        )
        event = session.slide_events.order_by('-entered_at', '-pk').first()
        return Response({
            'session_id': session.pk,
            'active': session.ended_at is None,
            'slide_event_id': event.pk if event else None,
            'slide_id': event.slide_id if event else None,
            'cameras': [
                {
                    'id': link.camera_id,
                    'name': link.camera.camera_name,
                    'position': link.camera.position,
                }
                for link in session.session_cameras.all()
            ],
        })


def _pipeline_session_queryset():
    return ClassroomSession.objects.select_related(
        'subject__classroom',
    ).prefetch_related(
        Prefetch(
            'session_cameras',
            queryset=SessionCamera.objects.select_related('camera').order_by(
                'camera__position', 'camera_id',
            ),
            to_attr='_pipeline_camera_links',
        ),
        Prefetch(
            'camera_worker_statuses',
            queryset=CameraWorkerStatus.objects.order_by('camera_id'),
            to_attr='_pipeline_worker_statuses',
        ),
        Prefetch(
            'slide_events',
            queryset=SlideEvent.objects.order_by('-entered_at', '-pk'),
            to_attr='_pipeline_slide_events',
        ),
    )


def _session_camera_health(session):
    records = {
        record.camera_id: record
        for record in getattr(session, '_pipeline_worker_statuses', [])
    }
    return [
        _camera_runtime_payload(link, records.get(link.camera_id))
        for link in getattr(session, '_pipeline_camera_links', [])
    ]


class PipelineWorkDiscoveryView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        auth_error = _pipeline_auth_error(request)
        if auth_error:
            return auth_error
        sessions = _pipeline_session_queryset().filter(
            ended_at__isnull=True,
            session_cameras__isnull=False,
        ).distinct().order_by('pk')
        return Response({
            'sessions': [
                {
                    'session_id': session.pk,
                    'classroom_id': session.subject.classroom_id,
                    'slide_event_id': (
                        session._pipeline_slide_events[0].pk
                        if session._pipeline_slide_events else None
                    ),
                    'slide_id': (
                        session._pipeline_slide_events[0].slide_id
                        if session._pipeline_slide_events else None
                    ),
                    'cameras': _session_camera_health(session),
                }
                for session in sessions
            ],
        })


class CameraWorkerHeartbeatView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        auth_error = _pipeline_auth_error(request)
        if auth_error:
            return auth_error
        serializer = CameraWorkerHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            session = get_object_or_404(
                ClassroomSession.objects.select_for_update(),
                pk=data['session_id'],
            )
            link = get_object_or_404(
                SessionCamera.objects.select_related('camera'),
                session=session,
                camera_id=data['camera_id'],
            )
            if session.ended_at and data['state'] != CameraWorkerStatus.State.STOPPED:
                raise serializers.ValidationError({
                    'state': 'An ended session accepts only the Stopped state.',
                })

            record = CameraWorkerStatus.objects.select_for_update().filter(
                session=session,
                camera_id=link.camera_id,
            ).first()
            if record is None and data['state'] not in {
                CameraWorkerStatus.State.STARTING,
                CameraWorkerStatus.State.STOPPED,
            }:
                raise serializers.ValidationError({
                    'state': 'A camera worker must begin in Starting state.',
                })
            if record and data['state'] not in WORKER_STATE_TRANSITIONS[record.state]:
                raise serializers.ValidationError({
                    'state': f'Cannot transition from {record.state} to {data["state"]}.',
                })

            defaults = {
                'state': data['state'],
                'source_type': data['source_type'],
                'reason': data['reason'],
                'pipeline_version': data['pipeline_version'],
                'analysis_rate': data['analysis_rate'],
                'yolo_candidates': data['yolo_candidates'],
                'valid_faces': data['valid_faces'],
                'confirmed_students': data['confirmed_students'],
                'unclassified_students': data['unclassified_students'],
                'latest_counts': data['counts'],
                'last_heartbeat': timezone.now(),
            }
            record, created = CameraWorkerStatus.objects.update_or_create(
                session=session,
                camera_id=link.camera_id,
                defaults=defaults,
            )

        return Response(
            _camera_runtime_payload(link, record),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SessionCameraHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_object_or_404(
            _pipeline_session_queryset().filter(
                pk__in=sessions_for_user(request.user).values('pk'),
            ),
            pk=pk,
        )
        return Response({
            'session_id': session.pk,
            'active': session.ended_at is None,
            'cameras': _session_camera_health(session),
        })


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
