from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LessonProgress
from .pagination import paginated_response
from .permissions import IsOrganizationUser
from .session_access import sessions_for_user
from .session_lifecycle import finish_saved_lesson, locked_lesson, owned_lessons, prepare_continuation
from .session_preparation import expire_prepared_sessions
from .session_serializers import (
    ClassroomSessionSerializer, LessonContinueSerializer,
    LessonProgressSerializer, LessonRevisionSerializer,
)
from .views import _log_activity


class LessonListView(APIView):
    permission_classes = [IsOrganizationUser]

    def get(self, request):
        expire_prepared_sessions(user=request.user)
        lessons = owned_lessons(request.user).prefetch_related('meetings').order_by('-updated_at', '-pk')
        state = request.query_params.get('status', '').strip()
        if state:
            if state not in LessonProgress.State.values:
                raise serializers.ValidationError({'status': 'Choose active, saved, or completed.'})
            lessons = lessons.filter(state=state)
        search = request.query_params.get('search', '').strip()
        if search:
            lessons = lessons.filter(
                Q(presentation__title__icontains=search) | Q(subject__subject_name__icontains=search)
                | Q(subject__subject_code__icontains=search) | Q(classroom__room_code__icontains=search)
            )
        return paginated_response(request, lessons, lambda page: LessonProgressSerializer(page, many=True).data)


class LessonDetailView(APIView):
    permission_classes = [IsOrganizationUser]

    def get(self, request, pk):
        expire_prepared_sessions(user=request.user)
        lesson = get_object_or_404(owned_lessons(request.user).prefetch_related('meetings'), pk=pk)
        return Response(LessonProgressSerializer(lesson).data)


class LessonContinueView(APIView):
    permission_classes = [IsOrganizationUser]

    def post(self, request, pk):
        expire_prepared_sessions(user=request.user)
        data = LessonContinueSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with locked_lesson(request.user, pk) as lesson:
            session, created = prepare_continuation(lesson, data.validated_data)
            if created:
                _log_activity(request, f'Prepared continuation {session.pk} for lesson {lesson.pk}.')
            payload = ClassroomSessionSerializer(session).data
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class LessonFinishView(APIView):
    permission_classes = [IsOrganizationUser]

    def post(self, request, pk):
        expire_prepared_sessions(user=request.user)
        data = LessonRevisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with locked_lesson(request.user, pk) as lesson:
            if finish_saved_lesson(lesson, data.validated_data.get('expected_revision')):
                _log_activity(request, f'Finished saved lesson {lesson.pk}.')
            payload = LessonProgressSerializer(lesson).data
        return Response(payload)


class SessionDetailView(APIView):
    permission_classes = [IsOrganizationUser]

    def get(self, request, pk):
        expire_prepared_sessions(user=request.user)
        session = get_object_or_404(sessions_for_user(request.user), pk=pk)
        return Response(ClassroomSessionSerializer(session).data)
