from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report
from .report_generation import generate_report_content, report_storage_name
from .session_access import sessions_for_user
from .views import _log_activity


REPORT_TYPES = (('pdf', 'Session Summary'), ('csv', 'Engagement Data'))


class ReportCreateSerializer(serializers.Serializer):
    session = serializers.IntegerField()
    report_type = serializers.ChoiceField(choices=REPORT_TYPES)

    def validate_session(self, value):
        session = sessions_for_user(self.context['request'].user).filter(pk=value).first()
        if session is None:
            raise serializers.ValidationError('Select a session available to your account.')
        if session.ended_at is None:
            raise serializers.ValidationError('End the classroom session before generating a report.')
        return session


def _report_data(report):
    labels = dict(REPORT_TYPES)
    return {
        'id': report.pk,
        'session': report.session_id,
        'subject_code': report.session.subject.subject_code,
        'subject_name': report.session.subject.subject_name,
        'classroom': report.session.subject.classroom.room_code,
        'session_date': report.session.session_date,
        'report_name': labels.get(report.report_type, report.report_type.title()),
        'report_type': report.report_type,
        'format': report.report_type.upper(),
        'generated_by': report.generated_by.get_full_name() or report.generated_by.username,
        'generated_at': report.generated_at,
        'file_name': _download_name(report),
        'download_url': f'/api/auth/reports/{report.pk}/download/',
    }


def _download_name(report):
    code = report.session.subject.subject_code.lower().replace(' ', '-')
    date = report.session.session_date.isoformat()
    suffix = 'session-summary' if report.report_type == 'pdf' else 'engagement-data'
    return f'{code}-{date}-{suffix}.{report.report_type}'


def _reports_for_user(user):
    return (
        Report.objects.filter(session__in=sessions_for_user(user))
        .select_related(
            'generated_by', 'session', 'session__subject', 'session__subject__classroom',
        )
    )


class ReportOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = sessions_for_user(request.user).filter(ended_at__isnull=False).order_by('-started_at')
        return Response([
            {
                'id': session.pk,
                'subject_code': session.subject.subject_code,
                'subject_name': session.subject.subject_name,
                'classroom': session.subject.classroom.room_code,
                'session_date': session.session_date,
                'started_at': session.started_at,
                'ended_at': session.ended_at,
                'teacher_name': session.user.get_full_name() or session.user.username,
            }
            for session in sessions
        ])


class ReportListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = _reports_for_user(request.user).order_by('-generated_at', '-pk')
        return Response([_report_data(report) for report in reports])

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        session = serializer.validated_data['session']
        report_type = serializer.validated_data['report_type']
        content = generate_report_content(session, report_type, request.user)
        path = default_storage.save(
            report_storage_name(session, report_type),
            ContentFile(content),
        )
        try:
            report = Report.objects.create(
                session=session,
                generated_by=request.user,
                report_type=report_type,
                report_path=path,
            )
        except Exception:
            default_storage.delete(path)
            raise
        _log_activity(
            request,
            f'Generated {report_type.upper()} report for classroom session {session.pk}.',
        )
        return Response(_report_data(report), status=status.HTTP_201_CREATED)


class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        report = get_object_or_404(_reports_for_user(request.user), pk=pk)
        if not default_storage.exists(report.report_path):
            raise Http404
        content_type = 'application/pdf' if report.report_type == 'pdf' else 'text/csv'
        return FileResponse(
            default_storage.open(report.report_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=_download_name(report),
        )
