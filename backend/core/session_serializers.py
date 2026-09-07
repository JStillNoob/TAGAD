from pathlib import Path
import zipfile

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Camera,
    ClassroomSession,
    Presentation,
    PresentationSlide,
    SessionCamera,
    SlideEvent,
)
from .session_access import presentations_for_user, subjects_for_user


PRESENTATION_MIME_TYPES = {
    Presentation.FileType.PDF: {'application/pdf'},
    Presentation.FileType.PPTX: {
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    },
}


def validate_presentation_file(upload):
    extension = Path(upload.name).suffix.lower().lstrip('.')
    if extension not in Presentation.FileType.values:
        raise serializers.ValidationError('Upload a PDF or PPTX file.')

    maximum = getattr(settings, 'PRESENTATION_MAX_UPLOAD_BYTES', 50 * 1024 * 1024)
    if upload.size > maximum:
        raise serializers.ValidationError(
            f'The presentation must be {maximum // (1024 * 1024)} MB or smaller.',
        )

    if upload.content_type not in PRESENTATION_MIME_TYPES[extension]:
        raise serializers.ValidationError('The file type does not match its extension.')

    try:
        upload.seek(0)
        if extension == Presentation.FileType.PDF:
            if upload.read(5) != b'%PDF-':
                raise serializers.ValidationError('The uploaded file is not a valid PDF.')
        else:
            with zipfile.ZipFile(upload) as archive:
                names = set(archive.namelist())
                required = {'[Content_Types].xml', 'ppt/presentation.xml'}
                if not required.issubset(names):
                    raise serializers.ValidationError('The uploaded file is not a valid PPTX.')
                expanded_size = sum(item.file_size for item in archive.infolist())
                expanded_limit = getattr(
                    settings,
                    'PRESENTATION_MAX_EXPANDED_BYTES',
                    250 * 1024 * 1024,
                )
                if expanded_size > expanded_limit:
                    raise serializers.ValidationError('The PPTX expands beyond the allowed size.')
    except zipfile.BadZipFile as error:
        raise serializers.ValidationError('The uploaded file is not a valid PPTX.') from error
    finally:
        upload.seek(0)

    upload.presentation_file_type = extension
    return upload


class PresentationUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150)
    file = serializers.FileField()

    def validate_title(self, value):
        return value.strip()

    def validate_file(self, value):
        return validate_presentation_file(value)


class PresentationSlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PresentationSlide
        fields = ('id', 'slide_number', 'slide_title', 'image_url')
        read_only_fields = fields

    def get_image_url(self, slide):
        return reverse('presentation-slide-image', args=[slide.presentation_id, slide.pk])


class PresentationSerializer(serializers.ModelSerializer):
    uploader_name = serializers.SerializerMethodField()
    source_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    slides = PresentationSlideSerializer(many=True, read_only=True)

    class Meta:
        model = Presentation
        fields = (
            'id',
            'title',
            'file_name',
            'file_type',
            'processing_status',
            'processing_error',
            'total_slides',
            'uploaded_at',
            'uploader_name',
            'source_url',
            'preview_url',
            'slides',
        )
        read_only_fields = fields

    def get_uploader_name(self, presentation):
        return presentation.user.get_full_name() or presentation.user.username

    def get_source_url(self, presentation):
        return reverse('presentation-source', args=[presentation.pk])

    def get_preview_url(self, presentation):
        if presentation.processing_status != Presentation.ProcessingStatus.READY:
            return None
        return reverse('presentation-preview', args=[presentation.pk])


class SessionCreateSerializer(serializers.Serializer):
    subject = serializers.IntegerField()
    presentation = serializers.IntegerField()
    cameras = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        user = self.context['request'].user
        errors = {}
        subject = subjects_for_user(user).filter(pk=attrs['subject']).first()
        presentation = presentations_for_user(user).filter(pk=attrs['presentation']).first()

        if subject is None:
            errors['subject'] = 'Select a subject available to your account.'
        if presentation is None:
            errors['presentation'] = 'Select a presentation available to your account.'
        elif presentation.processing_status != Presentation.ProcessingStatus.READY:
            errors['presentation'] = 'The presentation must finish processing before use.'

        camera_ids = attrs.get('cameras', [])
        if len(camera_ids) != len(set(camera_ids)):
            errors['cameras'] = 'Do not select the same camera more than once.'
        elif subject:
            cameras = list(Camera.objects.filter(pk__in=camera_ids))
            if len(cameras) != len(camera_ids) or any(
                camera.classroom_id != subject.classroom_id
                or camera.status != Camera.Status.ACTIVE
                for camera in cameras
            ):
                errors['cameras'] = 'Select only active cameras configured for this classroom.'
            else:
                attrs['camera_objects'] = cameras

        if ClassroomSession.objects.filter(user=user, ended_at__isnull=True).exists():
            errors['detail'] = 'End your active session before starting another one.'

        if errors:
            raise serializers.ValidationError(errors)
        attrs['subject_object'] = subject
        attrs['presentation_object'] = presentation
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        session = ClassroomSession.objects.create(
            user=user,
            subject=validated_data['subject_object'],
            presentation=validated_data['presentation_object'],
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        SessionCamera.objects.bulk_create([
            SessionCamera(session=session, camera=camera)
            for camera in validated_data.get('camera_objects', [])
        ])
        first_slide = session.presentation.slides.order_by('slide_number').first()
        if first_slide:
            SlideEvent.objects.create(
                session=session,
                slide=first_slide,
                entered_at=session.started_at,
            )
        return session


class ClassroomSessionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    classroom = serializers.CharField(source='subject.classroom.room_code', read_only=True)
    presentation_title = serializers.CharField(source='presentation.title', read_only=True)
    presentation = PresentationSerializer(read_only=True)
    cameras = serializers.SerializerMethodField()
    current_slide = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = ClassroomSession
        fields = (
            'id',
            'user',
            'subject_name',
            'subject_code',
            'classroom',
            'presentation_title',
            'presentation',
            'cameras',
            'current_slide',
            'session_date',
            'started_at',
            'ended_at',
            'status',
            'duration_minutes',
        )
        read_only_fields = fields

    def get_cameras(self, session):
        return [
            {
                'id': item.camera_id,
                'name': item.camera.camera_name,
                'position': item.camera.position,
            }
            for item in session.session_cameras.all()
        ]

    def get_status(self, session):
        return 'completed' if session.ended_at else 'ongoing'

    def get_current_slide(self, session):
        event = session.slide_events.order_by('-entered_at', '-pk').first()
        return event.slide_id if event else None

    def get_duration_minutes(self, session):
        if not session.ended_at:
            return None
        return round((session.ended_at - session.started_at).total_seconds() / 60)
