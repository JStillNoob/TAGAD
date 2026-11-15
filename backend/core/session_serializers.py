from pathlib import Path
from uuid import uuid4
import zipfile

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from .models import (
    ClassroomSession,
    LessonProgress,
    Presentation,
    PresentationSlide,
)
from .session_lifecycle import create_meeting, lesson_blocker, resolve_resources


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
    request_id = serializers.UUIDField(default=uuid4)
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
    in_use = serializers.SerializerMethodField()
    is_archived = serializers.BooleanField(read_only=True)
    slides = PresentationSlideSerializer(many=True, read_only=True)

    class Meta:
        model = Presentation
        fields = (
            'id',
            'request_id',
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
            'in_use',
            'archived_at',
            'is_archived',
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

    def get_in_use(self, presentation):
        if hasattr(presentation, '_in_use'):
            return presentation._in_use
        return presentation.sessions.exists()


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
        resolve_resources(user, attrs['subject'], attrs['presentation'], attrs.get('cameras', []))
        if ClassroomSession.objects.filter(user=user, ended_at__isnull=True).exists():
            raise serializers.ValidationError({'detail': 'End your active session before starting another one.'})
        return attrs

    def create(self, validated_data):
        return create_meeting(
            self.context['request'].user, validated_data['subject'],
            validated_data['presentation'], validated_data.get('cameras', []),
            prepared=self.context.get('prepared', False),
        )


class StrictPositiveIntegerField(serializers.IntegerField):
    def __init__(self, **kwargs):
        super().__init__(min_value=1, **kwargs)

    def to_internal_value(self, data):
        if type(data) is not int:
            self.fail('invalid')
        return super().to_internal_value(data)


class LessonRevisionSerializer(serializers.Serializer):
    expected_revision = StrictPositiveIntegerField(required=False)


class SessionEndSerializer(LessonRevisionSerializer):
    action = serializers.ChoiceField(choices=ClassroomSession.EndAction.choices, default=ClassroomSession.EndAction.FINISH)


class SessionSlideSerializer(LessonRevisionSerializer):
    slide = StrictPositiveIntegerField()


class LessonContinueSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    expected_revision = StrictPositiveIntegerField()
    from_session = StrictPositiveIntegerField()
    cameras = serializers.ListField(child=StrictPositiveIntegerField(), default=list)

    def validate_cameras(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Do not select the same camera more than once.')
        return value


class LessonProgressSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.room_code', read_only=True)
    presentation_title = serializers.CharField(source='presentation.title', read_only=True)
    last_slide_number = serializers.IntegerField(source='last_slide.slide_number', read_only=True)
    total_slides = serializers.IntegerField(source='presentation.total_slides', read_only=True)

    class Meta:
        model = LessonProgress
        fields = (
            'id', 'organization', 'owner', 'subject', 'subject_name', 'classroom',
            'classroom_name', 'presentation', 'presentation_title', 'last_slide',
            'last_slide_number', 'total_slides', 'state', 'revision', 'created_at', 'updated_at',
        )
        read_only_fields = fields

    def to_representation(self, lesson):
        data = super().to_representation(lesson)
        meetings = list(lesson.meetings.all())
        prepared = next((meeting for meeting in meetings if not meeting.started_at and not meeting.ended_at), None)
        active = next((meeting for meeting in meetings if meeting.started_at and not meeting.ended_at), None)
        taught = [meeting for meeting in meetings if meeting.started_at]
        latest = max(taught, key=lambda meeting: (meeting.started_at, meeting.pk), default=None)
        reason = None
        if lesson.state != LessonProgress.State.SAVED:
            reason = 'This lesson is complete.' if lesson.state == LessonProgress.State.COMPLETED else 'This lesson has an active class.'
        elif prepared:
            reason = 'A continuation is already prepared. Start it or cancel preparation.'
        else:
            reason = lesson_blocker(lesson)
        data.update(
            prepared_session=prepared.pk if prepared else None,
            active_session=active.pk if active else None,
            latest_session=latest.pk if latest else None,
            last_taught_at=(latest.ended_at or latest.started_at) if latest else None,
            display_state='Preparing to Continue' if prepared else lesson.get_state_display(),
            can_continue=reason is None, blocking_reason=reason,
        )
        return data


class ClassroomSessionSerializer(serializers.ModelSerializer):
    lesson = LessonProgressSerializer(read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    classroom = serializers.CharField(source='subject.classroom.room_code', read_only=True)
    presentation_title = serializers.CharField(source='presentation.title', read_only=True)
    presentation = serializers.SerializerMethodField()
    cameras = serializers.SerializerMethodField()
    current_slide = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    is_archived = serializers.BooleanField(read_only=True)

    class Meta:
        model = ClassroomSession
        fields = (
            'id',
            'user',
            'subject',
            'subject_name',
            'subject_code',
            'classroom',
            'presentation_title',
            'presentation',
            'cameras',
            'current_slide',
            'session_date',
            'prepared_at',
            'started_at',
            'ended_at',
            'status',
            'duration_minutes',
            'archived_at',
            'is_archived',
            'lesson',
            'continued_from',
            'continuation_request_id',
            'end_action',
        )
        read_only_fields = fields

    def get_cameras(self, session):
        return [
            {
                'id': item.camera_id,
                'name': item.camera.camera_name,
                'position': item.camera.position,
                'position_label': item.camera.get_position_display(),
                'status': item.camera.status,
                'status_label': item.camera.get_status_display(),
            }
            for item in session.session_cameras.all()
        ]

    def get_presentation(self, session):
        # A presentation reached through a session is necessarily protected.
        session.presentation._in_use = True
        return PresentationSerializer(session.presentation, context=self.context).data

    def get_status(self, session):
        if session.started_at is None and session.ended_at is None:
            return 'preparing'
        return 'completed' if session.ended_at else 'ongoing'

    def get_current_slide(self, session):
        ordered_events = getattr(session, '_ordered_slide_events', None)
        if ordered_events is None:
            event = session.slide_events.order_by('-entered_at', '-pk').first()
        else:
            event = ordered_events[0] if ordered_events else None
        return event.slide_id if event else (session.lesson.last_slide_id if session.lesson_id else None)

    def get_duration_minutes(self, session):
        if not session.started_at or not session.ended_at:
            return None
        return round((session.ended_at - session.started_at).total_seconds() / 60)
