from django.db.models import Exists, OuterRef, Prefetch, Q

from .models import ClassroomSession, Presentation, SlideEvent, Subject, User


def meeting_context(session):
    return {
        'lesson_id': session.lesson_id,
        'lesson_state': session.lesson.state if session.lesson_id else None,
        'end_action': session.end_action,
        'continued_from': session.continued_from_id,
    }


def presentations_for_user(user):
    presentations = Presentation.objects.select_related('user', 'user__organization').prefetch_related(
        'slides',
    ).annotate(
        _in_use=Exists(ClassroomSession.objects.filter(presentation_id=OuterRef('pk'))),
    )
    if user.role == User.Role.SYSTEM_ADMIN:
        return presentations
    if user.role == User.Role.ORG_ADMIN:
        return presentations.filter(user__organization=user.organization)
    return presentations.filter(user=user)


def presentations_for_update(user):
    return presentations_for_user(user).select_for_update(of=('self',))


def subjects_for_user(user):
    subjects = Subject.objects.select_related(
        'classroom', 'classroom__organization', 'teacher',
    ).prefetch_related('classroom__cameras')
    if user.role == User.Role.SYSTEM_ADMIN:
        return subjects
    if user.role == User.Role.ORG_ADMIN:
        return subjects.filter(classroom__organization=user.organization)
    return subjects.filter(teacher=user)


def sessions_for_user(user):
    sessions = ClassroomSession.objects.select_related(
        'user',
        'subject',
        'subject__classroom',
        'presentation',
        'presentation__user',
        'lesson__owner',
        'lesson__organization',
        'lesson__subject',
        'lesson__classroom',
        'lesson__presentation__user',
        'lesson__last_slide',
    ).prefetch_related(
        'session_cameras__camera',
        'presentation__slides',
        'lesson__meetings',
        Prefetch(
            'slide_events',
            queryset=SlideEvent.objects.order_by('-entered_at', '-pk'),
            to_attr='_ordered_slide_events',
        ),
    )
    if user.role == User.Role.SYSTEM_ADMIN:
        return sessions
    sessions = sessions.filter(
        Q(lesson__isnull=True, subject__classroom__organization_id=user.organization_id)
        | Q(lesson__organization_id=user.organization_id)
    )
    if user.role == User.Role.ORG_ADMIN:
        return sessions
    return sessions.filter(user=user)
