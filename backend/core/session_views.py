import mimetypes
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Camera, CameraWorkerStatus, ClassroomSession, Presentation, SlideEvent
from .lifecycle import archive_record, filter_lifecycle, restore_record
from .pagination import paginated_response
from .presentation_processing import delete_presentation_files, process_presentation
from .session_access import (
    presentations_for_update,
    presentations_for_user,
    sessions_for_user,
    subjects_for_user,
)
from .session_serializers import (
    ClassroomSessionSerializer,
    PresentationSerializer,
    PresentationUploadSerializer,
    SessionCreateSerializer,
)
from .session_preparation import expire_prepared_sessions
from .views import _log_activity


class PresentationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        presentations = filter_lifecycle(
            presentations_for_user(request.user),
            request.query_params.get('lifecycle'),
        ).order_by('-uploaded_at', '-pk')
        search = request.query_params.get('search', '').strip()
        if search:
            presentations = presentations.filter(
                Q(title__icontains=search) | Q(file_name__icontains=search),
            )
        processing_status = request.query_params.get('status', '').strip()
        if processing_status:
            presentations = presentations.filter(processing_status=processing_status)
        return paginated_response(
            request,
            presentations,
            lambda page: PresentationSerializer(page, many=True).data,
        )

    def post(self, request):
        serializer = PresentationUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_id = serializer.validated_data['request_id']
        existing = Presentation.objects.filter(
            user=request.user,
            request_id=request_id,
        ).first()
        if existing:
            return Response(PresentationSerializer(existing).data)
        upload = serializer.validated_data['file']
        presentation = Presentation(
            user=request.user,
            request_id=request_id,
            title=serializer.validated_data['title'],
            file_name=upload.name,
            file_path=upload,
            file_type=upload.presentation_file_type,
        )
        try:
            presentation.save()
        except IntegrityError:
            if presentation.file_path:
                presentation.file_path.delete(save=False)
            existing = Presentation.objects.filter(
                user=request.user,
                request_id=request_id,
            ).first()
            if existing:
                return Response(PresentationSerializer(existing).data)
            raise
        process_presentation(presentation)
        _log_activity(request, f'Uploaded presentation {presentation.pk} ({presentation.title}).')
        return Response(
            PresentationSerializer(presentation).data,
            status=status.HTTP_201_CREATED,
        )


class PresentationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(presentations_for_user(request.user), pk=pk)

    def get(self, request, pk):
        return Response(PresentationSerializer(self.get_object(request, pk)).data)

    def delete(self, request, pk):
        with transaction.atomic():
            presentation = get_object_or_404(
                presentations_for_update(request.user),
                pk=pk,
            )
            if presentation.sessions.filter(ended_at__isnull=True).exists():
                raise serializers.ValidationError({
                    'detail': 'End the active classroom session before archiving this presentation.',
                })
            if presentation.sessions.exists():
                if archive_record(presentation, request.user):
                    _log_activity(
                        request,
                        f'Archived presentation {presentation.pk} ({presentation.title}).',
                    )
            else:
                delete_presentation_files(presentation)
                description = f'Deleted unused presentation {presentation.pk} ({presentation.title}).'
                presentation.delete()
                _log_activity(request, description)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PresentationRestoreView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            presentation = get_object_or_404(
                presentations_for_update(request.user),
                pk=pk,
            )
            if restore_record(presentation):
                _log_activity(
                    request,
                    f'Restored presentation {presentation.pk} ({presentation.title}).',
                )
        return Response(PresentationSerializer(presentation).data)


class PresentationRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            presentation = get_object_or_404(
                presentations_for_update(request.user),
                pk=pk,
            )
            if presentation.is_archived:
                raise serializers.ValidationError({
                    'detail': 'Restore this presentation before retrying it.',
                })
            if presentation.processing_status == Presentation.ProcessingStatus.READY:
                return Response(PresentationSerializer(presentation).data)
            if presentation.processing_status == Presentation.ProcessingStatus.PROCESSING:
                return Response(
                    PresentationSerializer(presentation).data,
                    status=status.HTTP_202_ACCEPTED,
                )
            presentation.processing_status = Presentation.ProcessingStatus.PROCESSING
            presentation.processing_error = ''
            presentation.save(update_fields=['processing_status', 'processing_error'])

        process_presentation(presentation)
        _log_activity(request, f'Retried presentation {presentation.pk} ({presentation.title}).')
        return Response(PresentationSerializer(presentation).data)


class PresentationFileMixin:
    permission_classes = [IsAuthenticated]

    def get_presentation(self, request, pk):
        return get_object_or_404(presentations_for_user(request.user), pk=pk)


class PresentationSourceView(PresentationFileMixin, APIView):
    def get(self, request, pk):
        presentation = self.get_presentation(request, pk)
        if not presentation.file_path:
            raise Http404
        content_type = mimetypes.guess_type(presentation.file_name)[0] or 'application/octet-stream'
        return FileResponse(
            presentation.file_path.open('rb'),
            content_type=content_type,
            as_attachment=False,
            filename=presentation.file_name,
        )


@method_decorator(xframe_options_sameorigin, name='dispatch')
class PresentationPreviewView(PresentationFileMixin, APIView):
    def get(self, request, pk):
        presentation = self.get_presentation(request, pk)
        preview = presentation.preview_path if presentation.file_type == Presentation.FileType.PPTX else presentation.file_path
        if presentation.processing_status != Presentation.ProcessingStatus.READY or not preview:
            raise Http404
        return FileResponse(preview.open('rb'), content_type='application/pdf')


class PresentationSlideImageView(PresentationFileMixin, APIView):
    def get(self, request, pk, slide_pk):
        presentation = self.get_presentation(request, pk)
        slide = get_object_or_404(presentation.slides, pk=slide_pk)
        if not slide.image_path:
            raise Http404
        return FileResponse(slide.image_path.open('rb'), content_type='image/png')


class SessionOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'simulator_enabled': bool(settings.DEBUG and settings.ENABLE_PIPELINE_SIMULATOR),
        })


def _session_subject_data(subject):
    return {
        'id': subject.pk,
        'code': subject.subject_code,
        'name': subject.subject_name,
        'classroom': {
            'id': subject.classroom_id,
            'room_code': subject.classroom.room_code,
            'building': subject.classroom.building,
        },
        'cameras': [
            {
                'id': camera.pk,
                'name': camera.camera_name,
                'position': camera.position,
                'position_label': camera.get_position_display(),
                'status': camera.status,
                'status_label': camera.get_status_display(),
            }
            for camera in subject.classroom.cameras.all()
            if camera.status == Camera.Status.ACTIVE and not camera.is_archived
        ],
    }


class SessionSubjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subjects = subjects_for_user(request.user).filter(
            archived_at__isnull=True,
            classroom__archived_at__isnull=True,
            classroom__organization__archived_at__isnull=True,
            classroom__organization__status='active',
            teacher__status='active',
            teacher__is_active=True,
        )
        search = request.query_params.get('search', '').strip()
        if search:
            subjects = subjects.filter(
                Q(subject_code__icontains=search)
                | Q(subject_name__icontains=search)
                | Q(classroom__room_code__icontains=search)
                | Q(classroom__building__icontains=search)
            )
        selected = request.query_params.get('selected', '').strip()
        if selected.isdigit() and not search:
            subjects = subjects.annotate(
                _selected_order=Case(
                    When(pk=int(selected), then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
            ).order_by('_selected_order', 'subject_code', 'pk')
        else:
            subjects = subjects.order_by('subject_code', 'pk')
        return paginated_response(request, subjects, lambda page: [
            _session_subject_data(subject) for subject in page
        ])


class SessionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expire_prepared_sessions(user=request.user)
        sessions = filter_lifecycle(
            sessions_for_user(request.user),
            request.query_params.get('lifecycle'),
        )
        search = request.query_params.get('search', '').strip()
        if search:
            sessions = sessions.filter(
                Q(subject__subject_code__icontains=search)
                | Q(subject__subject_name__icontains=search)
                | Q(subject__classroom__room_code__icontains=search)
                | Q(presentation__title__icontains=search)
                | Q(user__username__icontains=search)
            )
        session_status = request.query_params.get('status', '').strip()
        if session_status == 'preparing':
            sessions = sessions.filter(started_at__isnull=True, ended_at__isnull=True)
            sessions = sessions.order_by('-prepared_at', '-pk')
        elif session_status == 'ongoing':
            sessions = sessions.filter(started_at__isnull=False, ended_at__isnull=True)
            sessions = sessions.order_by('-started_at', '-pk')
        elif session_status == 'completed':
            sessions = sessions.filter(ended_at__isnull=False)
            sessions = sessions.order_by('-started_at', '-pk')
        else:
            sessions = sessions.filter(started_at__isnull=False)
            sessions = sessions.order_by('-started_at', '-pk')
        return paginated_response(
            request,
            sessions,
            lambda page: ClassroomSessionSerializer(page, many=True).data,
        )

    def post(self, request):
        expire_prepared_sessions(user=request.user)
        serializer = SessionCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                session = serializer.save()
        except IntegrityError:
            raise serializers.ValidationError({
                'detail': 'End your active session before starting another one.',
            })
        _log_activity(request, f'Started classroom session {session.pk}.')
        return Response(
            ClassroomSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class SessionPrepareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        expire_prepared_sessions(user=request.user)
        serializer = SessionCreateSerializer(
            data=request.data,
            context={'request': request, 'prepared': True},
        )
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                session = serializer.save()
        except IntegrityError:
            raise serializers.ValidationError({
                'detail': 'Finish or cancel your current session preparation first.',
            })
        _log_activity(request, f'Prepared classroom session {session.pk}.')
        return Response(
            ClassroomSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class OwnedSessionMixin:
    permission_classes = [IsAuthenticated]

    def get_session(self, request, pk, *, for_update=False):
        sessions = sessions_for_user(request.user).filter(user=request.user)
        if for_update:
            sessions = sessions.select_for_update()
        return get_object_or_404(sessions, pk=pk)


class SessionStartView(OwnedSessionMixin, APIView):
    def post(self, request, pk):
        expire_prepared_sessions(user=request.user)
        with transaction.atomic():
            session = self.get_session(request, pk, for_update=True)
            if session.ended_at:
                raise serializers.ValidationError({'detail': 'This session has already ended.'})
            if session.started_at:
                return Response(ClassroomSessionSerializer(session).data)

            front_camera = session.session_cameras.filter(
                camera__position=Camera.Position.FRONT,
            ).first()
            if front_camera:
                heartbeat_cutoff = timezone.now() - timedelta(
                    seconds=max(1, settings.PIPELINE_HEARTBEAT_TIMEOUT_SECONDS),
                )
                front_online = CameraWorkerStatus.objects.filter(
                    session=session,
                    camera_id=front_camera.camera_id,
                    state=CameraWorkerStatus.State.ONLINE,
                    last_heartbeat__gte=heartbeat_cutoff,
                ).exists()
                if not front_online:
                    raise serializers.ValidationError({
                        'detail': 'Wait for the Front camera to become Online before starting.',
                    })

            started_at = timezone.now()
            session.started_at = started_at
            session.session_date = timezone.localdate(started_at)
            session.save(update_fields=['started_at', 'session_date'])
            first_slide = session.presentation.slides.order_by('slide_number').first()
            if first_slide:
                SlideEvent.objects.create(
                    session=session,
                    slide=first_slide,
                    entered_at=started_at,
                )
            _log_activity(request, f'Started classroom session {session.pk}.')
        return Response(ClassroomSessionSerializer(session).data)


class SessionPreparationCancelView(OwnedSessionMixin, APIView):
    def delete(self, request, pk):
        expire_prepared_sessions(user=request.user)
        with transaction.atomic():
            session = self.get_session(request, pk, for_update=True)
            if session.started_at or session.ended_at:
                raise serializers.ValidationError({
                    'detail': 'Only an unfinished session preparation can be cancelled.',
                })
            session_id = session.pk
            session.delete()
            _log_activity(request, f'Cancelled classroom session preparation {session_id}.')
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionEndView(OwnedSessionMixin, APIView):
    def post(self, request, pk):
        with transaction.atomic():
            session = self.get_session(request, pk, for_update=True)
            if session.started_at is None:
                raise serializers.ValidationError({
                    'detail': 'Cancel this preparation instead of ending it.',
                })
            if session.ended_at is None:
                session.ended_at = timezone.now()
                session.save(update_fields=['ended_at'])
                _log_activity(request, f'Ended classroom session {session.pk}.')
        return Response(ClassroomSessionSerializer(session).data)


class SessionLifecycleView(APIView):
    permission_classes = [IsAuthenticated]

    def get_session(self, request, pk):
        return get_object_or_404(sessions_for_user(request.user), pk=pk)

    def delete(self, request, pk):
        session = self.get_session(request, pk)
        if session.ended_at is None:
            raise serializers.ValidationError({
                'detail': 'End this classroom session before archiving it.',
            })
        if archive_record(session, request.user):
            _log_activity(request, f'Archived classroom session {session.pk}.')
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, pk):
        session = self.get_session(request, pk)
        if restore_record(session):
            _log_activity(request, f'Restored classroom session {session.pk}.')
        return Response(ClassroomSessionSerializer(session).data)


class SessionEnterSlideView(OwnedSessionMixin, APIView):
    def post(self, request, pk):
        with transaction.atomic():
            session = self.get_session(request, pk, for_update=True)
            if session.ended_at:
                raise serializers.ValidationError({'detail': 'This session has already ended.'})
            if session.started_at is None:
                raise serializers.ValidationError({'detail': 'Start the session before changing slides.'})
            slide = get_object_or_404(
                session.presentation.slides,
                pk=request.data.get('slide'),
            )
            current_event = session.slide_events.order_by('-entered_at', '-pk').first()
            if current_event and current_event.slide_id == slide.pk:
                return Response({'id': current_event.pk, 'created': False})
            event = SlideEvent.objects.create(
                session=session,
                slide=slide,
                entered_at=timezone.now(),
            )
        return Response(
            {'id': event.pk, 'created': True},
            status=status.HTTP_201_CREATED,
        )
