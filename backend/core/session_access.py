from .models import ClassroomSession, Presentation, Subject, User


def presentations_for_user(user):
    presentations = Presentation.objects.select_related('user', 'user__organization').prefetch_related(
        'slides',
    )
    if user.role == User.Role.SYSTEM_ADMIN:
        return presentations
    if user.role == User.Role.ORG_ADMIN:
        return presentations.filter(user__organization=user.organization)
    return presentations.filter(user=user)


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
    ).prefetch_related(
        'session_cameras__camera',
        'presentation__slides',
        'slide_events',
    )
    if user.role == User.Role.SYSTEM_ADMIN:
        return sessions
    if user.role == User.Role.ORG_ADMIN:
        return sessions.filter(subject__classroom__organization=user.organization)
    return sessions.filter(user=user)
