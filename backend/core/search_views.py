from urllib.parse import urlencode

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Classroom, User
from .session_access import presentations_for_user, sessions_for_user, subjects_for_user


RESULTS_PER_TYPE = 5


def _users_for_user(user):
    users = User.objects.select_related('organization')
    if user.role == User.Role.SYSTEM_ADMIN:
        return users
    if user.role == User.Role.ORG_ADMIN:
        return users.filter(organization=user.organization)
    return users.filter(pk=user.pk)


def _classrooms_for_user(user):
    classrooms = Classroom.objects.select_related('organization')
    if user.role == User.Role.SYSTEM_ADMIN:
        return classrooms
    if user.role == User.Role.ORG_ADMIN:
        return classrooms.filter(organization=user.organization)
    return classrooms.filter(subjects__teacher=user).distinct()


def _query_url(path, **parameters):
    return f'{path}?{urlencode(parameters)}'


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})

        users = _users_for_user(request.user).filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        ).order_by('first_name', 'last_name', 'username')[:RESULTS_PER_TYPE]
        classrooms = _classrooms_for_user(request.user).filter(
            Q(room_code__icontains=query)
            | Q(building__icontains=query)
            | Q(organization__organization_name__icontains=query)
        ).order_by('room_code')[:RESULTS_PER_TYPE]
        subjects = subjects_for_user(request.user).filter(
            Q(subject_code__icontains=query)
            | Q(subject_name__icontains=query)
            | Q(classroom__room_code__icontains=query)
            | Q(teacher__first_name__icontains=query)
            | Q(teacher__last_name__icontains=query)
        ).order_by('subject_code')[:RESULTS_PER_TYPE]
        sessions = sessions_for_user(request.user).filter(
            Q(subject__subject_code__icontains=query)
            | Q(subject__subject_name__icontains=query)
            | Q(subject__classroom__room_code__icontains=query)
            | Q(presentation__title__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        ).order_by('-started_at')[:RESULTS_PER_TYPE]
        presentations = presentations_for_user(request.user).filter(
            Q(title__icontains=query)
            | Q(file_name__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        ).order_by('-uploaded_at')[:RESULTS_PER_TYPE]

        results = []
        for user in users:
            results.append({
                'type': 'user',
                'id': user.pk,
                'title': user.get_full_name() or user.username,
                'subtitle': f'{user.username} · {user.get_role_display()}',
                'url': (
                    _query_url('/users', search=user.username)
                    if request.user.role in (User.Role.SYSTEM_ADMIN, User.Role.ORG_ADMIN)
                    else '/settings'
                ),
            })
        for classroom in classrooms:
            results.append({
                'type': 'classroom',
                'id': classroom.pk,
                'title': classroom.room_code,
                'subtitle': f'{classroom.building or "Building not specified"} · {classroom.organization.organization_name}',
                'url': _query_url('/classes', search=classroom.room_code),
            })
        for subject in subjects:
            results.append({
                'type': 'subject',
                'id': subject.pk,
                'title': f'{subject.subject_code} — {subject.subject_name}',
                'subtitle': f'{subject.classroom.room_code} · {subject.teacher.get_full_name() or subject.teacher.username}',
                'url': _query_url('/classes', search=subject.subject_code),
            })
        for session in sessions:
            status_label = 'Ongoing' if session.ended_at is None else 'Completed'
            results.append({
                'type': 'session',
                'id': session.pk,
                'title': f'{session.subject.subject_code} session',
                'subtitle': f'{session.session_date:%b %d, %Y} · {status_label}',
                'url': _query_url('/analytics', session=session.pk),
            })
        for presentation in presentations:
            results.append({
                'type': 'presentation',
                'id': presentation.pk,
                'title': presentation.title,
                'subtitle': f'{presentation.file_name} · {presentation.total_slides} slides',
                'url': _query_url('/session', presentation=presentation.pk),
            })
        return Response({'results': results})
