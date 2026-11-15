from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import (
    Camera, CameraWorkerStatus, ClassroomSession, LessonProgress, Organization,
    Presentation, SessionCamera, SlideEvent, User,
)
from .session_access import presentations_for_user, sessions_for_user, subjects_for_user


class SessionConflict(APIException):
    status_code = 409

    def __init__(self, code, detail, *, lesson=None, session=None):
        self.detail = {'code': code, 'detail': detail}
        if lesson is not None:
            self.detail.update(lesson_id=lesson.pk, lesson_revision=lesson.revision)
        if session is not None:
            self.detail.update(
                session_id=session.pk, end_action=session.end_action,
                session_state='completed' if session.ended_at else (
                    'ongoing' if session.started_at else 'preparing'
                ),
            )


def owned_lessons(user):
    return LessonProgress.objects.filter(owner=user, organization_id=user.organization_id).select_related(
        'owner', 'organization', 'subject', 'classroom', 'presentation__user', 'last_slide',
    )


@contextmanager
def locked_lesson(user, lesson_id):
    # User -> presentation -> lesson -> meeting is shared with preparation cleanup.
    with transaction.atomic():
        actor = User.objects.select_for_update().get(pk=user.pk)
        reference = owned_lessons(actor).filter(pk=lesson_id).values('presentation_id').first()
        if reference is None:
            raise Http404
        Presentation.objects.select_for_update().get(pk=reference['presentation_id'])
        lesson = owned_lessons(actor).select_for_update(of=('self',)).get(pk=lesson_id)
        yield lesson


@contextmanager
def locked_meeting(session_id, *, user=None, owner_only=True):
    with transaction.atomic():
        query = ClassroomSession.objects.filter(pk=session_id)
        if user is not None:
            query = query.filter(pk__in=sessions_for_user(user).values('pk'))
            if owner_only:
                query = query.filter(user=user)
        reference = query.values('user_id').first()
        if reference is None:
            raise Http404
        actor = User.objects.select_for_update().get(pk=reference['user_id'])
        reference = query.values('presentation_id', 'lesson_id').first()
        if reference is None:
            raise Http404
        Presentation.objects.select_for_update().get(pk=reference['presentation_id'])
        if reference['lesson_id']:
            LessonProgress.objects.select_for_update().get(pk=reference['lesson_id'])
        session = query.select_related(
            'user', 'subject__classroom__organization', 'presentation', 'lesson__last_slide',
        ).select_for_update(of=('self',)).first()
        if session is None:
            raise Http404
        if user is not None:
            organization_id = session.lesson.organization_id if session.lesson_id else session.subject.classroom.organization_id
            requesting_organization = actor.organization_id if owner_only else user.organization_id
            if organization_id != requesting_organization:
                raise Http404
        yield session


def validate_revision(lesson, revision, *, required=False):
    if revision is None:
        if required:
            raise serializers.ValidationError({'expected_revision': 'Refresh the lesson and send its current revision.'})
        return
    if revision != lesson.revision:
        raise SessionConflict('stale_revision', 'This lesson changed in another request. Refresh it and try again.', lesson=lesson)


def save_progress(lesson):
    lesson.revision += 1
    lesson.save(update_fields=['state', 'last_slide', 'revision', 'updated_at'])


def resolve_resources(user, subject_id, presentation_id, camera_ids):
    errors = {}
    subject = subjects_for_user(user).filter(pk=subject_id).first()
    presentation = presentations_for_user(user).filter(pk=presentation_id).first()
    if subject is None:
        errors['subject'] = 'Select a subject available to your account.'
    elif (
        subject.is_archived or subject.classroom.is_archived
        or subject.classroom.organization.is_archived
        or subject.classroom.organization.status != Organization.Status.ACTIVE
        or subject.classroom.organization_id != user.organization_id
    ):
        errors['subject'] = 'Select an active subject and classroom in your organization.'
    if presentation is None:
        errors['presentation'] = 'Select a presentation available to your account.'
    elif presentation.is_archived:
        errors['presentation'] = 'Restore this presentation before using it.'
    elif presentation.processing_status != Presentation.ProcessingStatus.READY:
        errors['presentation'] = 'The presentation must finish processing before use.'
    cameras = list(Camera.objects.filter(pk__in=camera_ids))
    if len(set(camera_ids)) != len(camera_ids):
        errors['cameras'] = 'Do not select the same camera more than once.'
    elif subject and (
        len(cameras) != len(camera_ids) or any(
            camera.classroom_id != subject.classroom_id or camera.is_archived
            or camera.status != Camera.Status.ACTIVE for camera in cameras
        )
    ):
        errors['cameras'] = 'Select only active cameras configured for this classroom.'
    if not user.is_active or user.status != User.Status.ACTIVE:
        errors['detail'] = 'An active teaching account is required.'
    if errors:
        raise serializers.ValidationError(errors)
    return subject, presentation, cameras


def lesson_blocker(lesson):
    owner = lesson.owner
    if owner.organization_id != lesson.organization_id or not owner.is_active or owner.status != User.Status.ACTIVE:
        return 'Restore the lesson owner access before continuing.'
    if owner.role not in (User.Role.TEACHER, User.Role.ORG_ADMIN):
        return 'A teaching account is required to continue this lesson.'
    if lesson.organization.is_archived or lesson.organization.status != Organization.Status.ACTIVE:
        return 'Restore the organization before continuing.'
    if lesson.classroom.organization_id != lesson.organization_id or lesson.classroom.is_archived:
        return 'Restore the original classroom before continuing.'
    if lesson.subject.classroom_id != lesson.classroom_id or lesson.subject.is_archived:
        return 'Restore the original subject and classroom assignment before continuing.'
    if owner.role == User.Role.TEACHER and lesson.subject.teacher_id != owner.pk:
        return 'This subject is assigned to another teacher. Ask your organization admin to review it.'
    presentation = lesson.presentation
    if (
        presentation.is_archived or presentation.processing_status != Presentation.ProcessingStatus.READY
        or presentation.user.organization_id != lesson.organization_id
        or (owner.role == User.Role.TEACHER and presentation.user_id != owner.pk)
    ):
        return 'Restore the original ready presentation before continuing.'
    slide = lesson.last_slide
    if slide.presentation_id != presentation.pk:
        return 'The saved slide does not belong to this presentation. Ask your organization admin to review it.'
    try:
        files_available = (
            presentation.file_path and presentation.file_path.storage.exists(presentation.file_path.name)
            and slide.image_path and slide.image_path.storage.exists(slide.image_path.name)
        )
    except OSError:
        return 'The presentation storage is unavailable. Reconnect it before continuing.'
    if not files_available:
        return 'The saved presentation or slide file is unavailable. Restore its files before continuing.'
    return None


@transaction.atomic
def create_meeting(user, subject_id, presentation_id, camera_ids, *, prepared):
    actor = User.objects.select_for_update().get(pk=user.pk)
    # Lock only a presentation the actor can access.
    presentation = presentations_for_user(actor).filter(pk=presentation_id).first()
    if presentation is not None:
        Presentation.objects.select_for_update().get(pk=presentation.pk)
    subject, presentation, cameras = resolve_resources(actor, subject_id, presentation_id, camera_ids)
    if ClassroomSession.objects.filter(user=actor, ended_at__isnull=True).exists():
        raise serializers.ValidationError({'detail': 'End your active session before starting another one.'})
    session = ClassroomSession.objects.create(
        user=actor, subject=subject, presentation=presentation,
        session_date=timezone.localdate(),
    )
    SessionCamera.objects.bulk_create([SessionCamera(session=session, camera=camera) for camera in cameras])
    if not prepared:
        start_meeting(session, require_online=False)
    return session


def start_meeting(session, *, revision=None, require_online=True):
    if session.ended_at and not session.lesson_id:
        raise serializers.ValidationError({'detail': 'This session has already ended.'})
    if session.started_at:
        return
    if session.ended_at:
        raise serializers.ValidationError({'detail': 'This session has already ended.'})
    camera_ids = list(session.session_cameras.values_list('camera_id', flat=True))
    resolve_resources(session.user, session.subject_id, session.presentation_id, camera_ids)
    if session.lesson_id:
        lesson = session.lesson
        validate_revision(lesson, revision, required=True)
        blocker = lesson_blocker(lesson)
        if blocker:
            raise serializers.ValidationError({'detail': blocker})
        if lesson.state != LessonProgress.State.SAVED:
            raise SessionConflict('lesson_not_saved', 'This lesson is no longer saved for continuation.', lesson=lesson)
        slide = lesson.last_slide
    else:
        slide = session.presentation.slides.order_by('slide_number').first()
        if slide is None:
            raise serializers.ValidationError({'presentation': 'The presentation has no available slides.'})
    if require_online and camera_ids:
        cutoff = timezone.now() - timedelta(seconds=max(1, settings.PIPELINE_HEARTBEAT_TIMEOUT_SECONDS))
        online = CameraWorkerStatus.objects.filter(
            session=session, camera_id__in=camera_ids,
            state=CameraWorkerStatus.State.ONLINE, last_heartbeat__gte=cutoff,
        ).count()
        if online != len(camera_ids):
            raise serializers.ValidationError({'detail': 'Wait for all selected cameras to become Online before starting.'})
    started_at = timezone.now()
    if session.lesson_id:
        lesson.state = LessonProgress.State.ACTIVE
        save_progress(lesson)
    else:
        session.lesson = LessonProgress.objects.create(
            owner=session.user, organization_id=session.subject.classroom.organization_id,
            subject=session.subject, classroom=session.subject.classroom,
            presentation=session.presentation, last_slide=slide,
        )
    session.started_at = started_at
    session.session_date = timezone.localdate(started_at)
    session.save(update_fields=['lesson', 'started_at', 'session_date'])
    SlideEvent.objects.create(session=session, slide=slide, entered_at=started_at)


def cancel_preparation(session):
    if session.started_at or session.ended_at:
        raise serializers.ValidationError({'detail': 'Only an unfinished session preparation can be cancelled.'})
    if session.lesson_id:
        save_progress(session.lesson)
    return session.delete()[0]


def end_meeting(session, action, revision=None):
    if session.started_at is None:
        raise serializers.ValidationError({'detail': 'Cancel this preparation instead of ending it.'})
    if session.ended_at:
        committed = session.end_action or ClassroomSession.EndAction.FINISH
        if committed != action:
            raise SessionConflict('end_action_conflict', 'This meeting has already closed with a different action.', lesson=session.lesson, session=session)
        return False
    if session.lesson_id:
        validate_revision(session.lesson, revision, required=action == ClassroomSession.EndAction.SAVE)
        event = session.slide_events.order_by('-entered_at', '-pk').first()
        session.lesson.last_slide = event.slide
        session.lesson.state = LessonProgress.State.SAVED if action == ClassroomSession.EndAction.SAVE else LessonProgress.State.COMPLETED
        save_progress(session.lesson)
        session.end_action = action
    elif action == ClassroomSession.EndAction.SAVE:
        raise serializers.ValidationError({'detail': 'This class predates lesson continuation. Finish it normally, then start a new lesson.'})
    session.ended_at = timezone.now()
    session.save(update_fields=['ended_at', 'end_action'])
    return True


def prepare_continuation(lesson, data):
    existing = ClassroomSession.objects.filter(
        user=lesson.owner, continuation_request_id=data['request_id'],
    ).first()
    if existing:
        camera_ids = set(existing.session_cameras.values_list('camera_id', flat=True))
        if existing.lesson_id != lesson.pk or existing.continued_from_id != data['from_session'] or camera_ids != set(data['cameras']):
            raise SessionConflict('request_key_reused', 'This request key was already used for a different continuation.', lesson=lesson)
        return existing, False
    validate_revision(lesson, data['expected_revision'], required=True)
    if lesson.state != LessonProgress.State.SAVED:
        raise SessionConflict('lesson_not_saved', 'Only a saved lesson can be continued.', lesson=lesson)
    latest = lesson.meetings.filter(started_at__isnull=False).order_by('-started_at', '-pk').first()
    if latest is None or latest.pk != data['from_session'] or latest.end_action != ClassroomSession.EndAction.SAVE:
        raise SessionConflict('continuation_source_changed', 'Refresh this lesson before continuing its latest meeting.', lesson=lesson)
    unfinished = ClassroomSession.objects.filter(user=lesson.owner, ended_at__isnull=True).first()
    if unfinished:
        raise SessionConflict('unfinished_meeting', 'Finish or cancel your current class before continuing this lesson.', lesson=lesson, session=unfinished)
    blocker = lesson_blocker(lesson)
    if blocker:
        raise serializers.ValidationError({'detail': blocker})
    _, _, cameras = resolve_resources(lesson.owner, lesson.subject_id, lesson.presentation_id, data['cameras'])
    session = ClassroomSession.objects.create(
        user=lesson.owner, subject=lesson.subject, presentation=lesson.presentation,
        lesson=lesson, continued_from=latest, continuation_request_id=data['request_id'],
        session_date=timezone.localdate(),
    )
    SessionCamera.objects.bulk_create([SessionCamera(session=session, camera=camera) for camera in cameras])
    save_progress(lesson)
    return session, True


def finish_saved_lesson(lesson, revision):
    if lesson.state == LessonProgress.State.COMPLETED:
        return False
    validate_revision(lesson, revision, required=True)
    unfinished = lesson.meetings.filter(ended_at__isnull=True).first()
    if lesson.state != LessonProgress.State.SAVED or unfinished:
        raise SessionConflict('unfinished_meeting', 'Start or cancel this preparation, or end the active class first.', lesson=lesson, session=unfinished)
    lesson.state = LessonProgress.State.COMPLETED
    save_progress(lesson)
    return True
