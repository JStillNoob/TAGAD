from django.db.models import Exists, OuterRef, Prefetch

from .models import ClassroomSession, Presentation, SlideEvent, Subject, User


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
    ).prefetch_related(
        'session_cameras__camera',
        'presentation__slides',
        Prefetch(
            'slide_events',
            queryset=SlideEvent.objects.order_by('-entered_at', '-pk'),
            to_attr='_ordered_slide_events',
        ),
    )
    if user.role == User.Role.SYSTEM_ADMIN:
        return sessions
    if user.role == User.Role.ORG_ADMIN:
        return sessions.filter(subject__classroom__organization=user.organization)
    return sessions.filter(user=user)
