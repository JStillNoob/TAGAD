import mimetypes

from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Camera, ClassroomSession, Presentation, SlideEvent
from .presentation_processing import process_presentation
from .session_access import presentations_for_user, sessions_for_user, subjects_for_user
from .session_serializers import (
    ClassroomSessionSerializer,
    PresentationSerializer,
    PresentationUploadSerializer,
    SessionCreateSerializer,
)
from .views import _log_activity


class PresentationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        presentations = presentations_for_user(request.user).order_by('-uploaded_at')
        return Response(PresentationSerializer(presentations, many=True).data)

    def post(self, request):
        serializer = PresentationUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data['file']
        presentation = Presentation.objects.create(
            user=request.user,
            title=serializer.validated_data['title'],
            file_name=upload.name,
            file_path=upload,
            file_type=upload.presentation_file_type,
        )
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
        presentation = self.get_object(request, pk)
        if presentation.sessions.exists():
            raise serializers.ValidationError({
                'detail': 'A presentation used by a classroom session cannot be deleted.',
            })
        for slide in presentation.slides.all():
            if slide.image_path:
                slide.image_path.delete(save=False)
        if presentation.preview_path:
            presentation.preview_path.delete(save=False)
        if presentation.file_path:
            presentation.file_path.delete(save=False)
        description = f'Deleted presentation {presentation.pk} ({presentation.title}).'
        presentation.delete()
        _log_activity(request, description)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        subjects = subjects_for_user(request.user).order_by('subject_code')
        presentations = presentations_for_user(request.user).order_by('-uploaded_at')
        return Response({
            'subjects': [
                {
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
                        }
                        for camera in subject.classroom.cameras.all()
                        if camera.status == Camera.Status.ACTIVE
                    ],
                }
                for subject in subjects
            ],
            'presentations': PresentationSerializer(presentations, many=True).data,
        })


class SessionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = sessions_for_user(request.user).order_by('-started_at')
        return Response(ClassroomSessionSerializer(sessions, many=True).data)

    def post(self, request):
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


class OwnedSessionMixin:
    permission_classes = [IsAuthenticated]

    def get_session(self, request, pk):
        return get_object_or_404(
            sessions_for_user(request.user).filter(user=request.user),
            pk=pk,
        )


class SessionEndView(OwnedSessionMixin, APIView):
    def post(self, request, pk):
        session = self.get_session(request, pk)
        if session.ended_at:
            raise serializers.ValidationError({'detail': 'This session has already ended.'})
        session.ended_at = timezone.now()
        session.save(update_fields=['ended_at'])
        _log_activity(request, f'Ended classroom session {session.pk}.')
        return Response(ClassroomSessionSerializer(session).data)


class SessionEnterSlideView(OwnedSessionMixin, APIView):
    def post(self, request, pk):
        session = self.get_session(request, pk)
        if session.ended_at:
            raise serializers.ValidationError({'detail': 'This session has already ended.'})
        slide = get_object_or_404(
            session.presentation.slides,
            pk=request.data.get('slide'),
        )
        event = SlideEvent.objects.create(
            session=session,
            slide=slide,
            entered_at=timezone.now(),
        )
        return Response({'id': event.pk}, status=status.HTTP_201_CREATED)
