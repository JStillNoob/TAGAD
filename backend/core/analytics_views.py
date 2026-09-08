import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .analytics import build_session_analytics
from .session_access import sessions_for_user
from .views import _log_activity


def _previous_session(request, session):
    return (
        sessions_for_user(request.user)
        .filter(subject=session.subject, started_at__lt=session.started_at)
        .order_by('-started_at')
        .first()
    )


class AnalyticsSessionMixin:
    permission_classes = [IsAuthenticated]

    def get_session(self, request, pk):
        return get_object_or_404(sessions_for_user(request.user), pk=pk)

    def get_analytics(self, request, session):
        return build_session_analytics(
            session,
            previous_session=_previous_session(request, session),
        )


class AnalyticsSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = sessions_for_user(request.user).order_by('-started_at', '-pk')
        return Response([
            {
                'id': session.pk,
                'subject_code': session.subject.subject_code,
                'subject_name': session.subject.subject_name,
                'classroom': session.subject.classroom.room_code,
                'teacher_name': session.user.get_full_name() or session.user.username,
                'session_date': session.session_date,
                'started_at': session.started_at,
                'ended_at': session.ended_at,
                'status': 'completed' if session.ended_at else 'ongoing',
            }
            for session in sessions
        ])


class SessionAnalyticsView(AnalyticsSessionMixin, APIView):
    def get(self, request, pk):
        session = self.get_session(request, pk)
        return Response(self.get_analytics(request, session))


class SessionAnalyticsCsvView(AnalyticsSessionMixin, APIView):
    def get(self, request, pk):
        session = self.get_session(request, pk)
        analytics = self.get_analytics(request, session)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics-session-{session.pk}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Slide', 'Topic', 'Timestamp', 'Duration Seconds', 'Detected',
            'Engaged %', 'Attentive %', 'Confused %', 'Bored %',
            'Disengaged %', 'Average Confidence %',
        ])
        for slide in analytics['slides']:
            writer.writerow([
                slide['slide_number'],
                slide['title'],
                slide['entered_at'],
                slide['duration_seconds'],
                slide['detected'],
                slide['engaged'] if slide['engaged'] is not None else '',
                slide['attentive'] if slide['attentive'] is not None else '',
                slide['confused'] if slide['confused'] is not None else '',
                slide['bored'] if slide['bored'] is not None else '',
                slide['disengaged'] if slide['disengaged'] is not None else '',
                slide['average_confidence'] if slide['average_confidence'] is not None else '',
            ])
        _log_activity(request, f'Downloaded analytics CSV for classroom session {session.pk}.')
        return response
