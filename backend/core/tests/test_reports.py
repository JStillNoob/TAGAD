import tempfile
from datetime import timedelta

import pymupdf
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Classroom,
    ClassroomSession,
    EngagementSummary,
    Organization,
    Presentation,
    PresentationSlide,
    Report,
    SlideEvent,
    Subject,
    SystemLog,
    User,
)


class ReportTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University',
            organization_code='OTHER-U',
        )
        self.system_admin = User.objects.create_superuser(
            username='system.admin',
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='org.admin',
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            first_name='Terry',
            last_name='Teacher',
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='teacher.other',
            organization=self.other_organization,
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-101',
        )
        self.other_classroom = Classroom.objects.create(
            organization=self.other_organization,
            room_code='ROOM-201',
        )
        self.subject = Subject.objects.create(
            classroom=self.classroom,
            teacher=self.teacher,
            subject_code='IT-301',
            subject_name='Data Structures',
        )
        self.other_subject = Subject.objects.create(
            classroom=self.other_classroom,
            teacher=self.other_teacher,
            subject_code='IT-401',
            subject_name='Networks',
        )
        self.session = self.create_session(self.teacher, self.subject)
        self.other_session = self.create_session(self.other_teacher, self.other_subject)

    def create_session(self, user, subject, *, ended=True):
        presentation = Presentation.objects.create(
            user=user,
            title=f'{subject.subject_code} Presentation',
            file_name='lecture.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
            total_slides=1,
        )
        slide = PresentationSlide.objects.create(
            presentation=presentation,
            slide_number=1,
            slide_title='Introduction to Data',
        )
        started = timezone.now().replace(microsecond=0) - timedelta(minutes=15)
        session = ClassroomSession.objects.create(
            user=user,
            subject=subject,
            presentation=presentation,
            session_date=timezone.localdate(started),
            started_at=started,
            ended_at=started + timedelta(minutes=10) if ended else None,
        )
        event = SlideEvent.objects.create(session=session, slide=slide, entered_at=started)
        if ended:
            EngagementSummary.objects.create(
                event=event,
                engaged_count=8,
                attentive_count=1,
                confused_count=1,
                total_detected=10,
                average_confidence='92.50',
            )
        return session

    def generate(self, session=None, report_type='pdf'):
        return self.client.post(
            reverse('report-list-create'),
            {'session': (session or self.session).pk, 'report_type': report_type},
            content_type='application/json',
        )

    def response_bytes(self, response):
        content = b''.join(response.streaming_content)
        response.close()
        return content

    def test_pdf_generation_creates_polished_valid_report_and_metadata(self):
        self.client.force_login(self.teacher)

        response = self.generate()

        self.assertEqual(response.status_code, 201)
        report = Report.objects.get(pk=response.json()['id'])
        self.assertEqual(report.report_type, 'pdf')
        self.assertTrue(default_storage.exists(report.report_path))
        with default_storage.open(report.report_path, 'rb') as report_file:
            content = report_file.read()
        self.assertTrue(content.startswith(b'%PDF-'))
        document = pymupdf.open(stream=content, filetype='pdf')
        text = ''.join(page.get_text() for page in document)
        document.close()
        self.assertIn('TAGAD', text)
        self.assertIn('Post-Lesson Engagement Report', text)
        self.assertIn('IT-301 - Data Structures', text)
        self.assertIn('Engagement Distribution', text)
        self.assertIn('Slide-by-Slide Breakdown', text)
        self.assertTrue(SystemLog.objects.filter(
            user=self.teacher,
            activity=f'Generated PDF report for classroom session {self.session.pk}.',
        ).exists())

    def test_csv_generation_and_download_contain_raw_analytics(self):
        self.client.force_login(self.teacher)

        created = self.generate(report_type='csv')
        report = Report.objects.get(pk=created.json()['id'])
        downloaded = self.client.get(reverse('report-download', args=[report.pk]))
        content = self.response_bytes(downloaded).decode('utf-8')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded['Content-Type'], 'text/csv')
        self.assertIn('it-301-', downloaded['Content-Disposition'])
        self.assertIn('engagement-data.csv', downloaded['Content-Disposition'])
        self.assertIn('Slide,Topic,Timestamp,Duration Seconds,Detected', content)
        self.assertIn('1,Introduction to Data', content)

    def test_list_and_options_are_role_scoped(self):
        own_report = Report.objects.create(
            session=self.session,
            generated_by=self.teacher,
            report_type='pdf',
            report_path='reports/own.pdf',
        )
        foreign_report = Report.objects.create(
            session=self.other_session,
            generated_by=self.other_teacher,
            report_type='pdf',
            report_path='reports/foreign.pdf',
        )
        self.client.force_login(self.teacher)
        teacher_reports = self.client.get(reverse('report-list-create')).json()
        teacher_options = self.client.get(reverse('report-options')).json()
        self.client.force_login(self.org_admin)
        org_reports = self.client.get(reverse('report-list-create')).json()
        self.client.force_login(self.system_admin)
        system_reports = self.client.get(reverse('report-list-create')).json()

        self.assertEqual([item['id'] for item in teacher_reports], [own_report.pk])
        self.assertEqual([item['id'] for item in teacher_options], [self.session.pk])
        self.assertEqual([item['id'] for item in org_reports], [own_report.pk])
        self.assertEqual({item['id'] for item in system_reports}, {own_report.pk, foreign_report.pk})

    def test_generation_rejects_foreign_ongoing_and_invalid_types(self):
        ongoing = self.create_session(self.teacher, self.subject, ended=False)
        self.client.force_login(self.teacher)

        foreign = self.generate(self.other_session)
        unfinished = self.generate(ongoing)
        invalid_type = self.generate(report_type='docx')

        self.assertEqual(foreign.status_code, 400)
        self.assertIn('session', foreign.json())
        self.assertEqual(unfinished.status_code, 400)
        self.assertIn('session', unfinished.json())
        self.assertEqual(invalid_type.status_code, 400)
        self.assertIn('report_type', invalid_type.json())
        self.assertEqual(Report.objects.count(), 0)

    def test_report_download_is_scoped_and_missing_file_returns_404(self):
        report = Report.objects.create(
            session=self.other_session,
            generated_by=self.other_teacher,
            report_type='pdf',
            report_path='reports/missing.pdf',
        )
        self.client.force_login(self.teacher)
        foreign = self.client.get(reverse('report-download', args=[report.pk]))
        self.client.force_login(self.system_admin)
        missing = self.client.get(reverse('report-download', args=[report.pk]))

        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(missing.status_code, 404)

    def test_report_endpoints_require_authentication(self):
        list_response = self.client.get(reverse('report-list-create'))
        options_response = self.client.get(reverse('report-options'))
        create_response = self.generate()

        self.assertIn(list_response.status_code, (401, 403))
        self.assertIn(options_response.status_code, (401, 403))
        self.assertIn(create_response.status_code, (401, 403))
