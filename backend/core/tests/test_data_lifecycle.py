import io
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings
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


class DataLifecycleCleanupTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
            RETENTION_FAILED_PRESENTATION_DAYS=30,
            RETENTION_REPORT_DAYS=365,
            RETENTION_ENGAGEMENT_SUMMARY_DAYS=180,
            RETENTION_SYSTEM_LOG_DAYS=180,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.organization = Organization.objects.create(
            organization_name='Lifecycle University',
            organization_code='LIFE-U',
        )
        self.teacher = User.objects.create_user(
            username='lifecycle.teacher',
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='LIFE-101',
        )
        self.subject = Subject.objects.create(
            classroom=self.classroom,
            teacher=self.teacher,
            subject_code='LIFE-1',
            subject_name='Lifecycle Testing',
        )
        self.now = timezone.now()

    def presentation(self, title, *, status, age_days):
        presentation = Presentation.objects.create(
            user=self.teacher,
            title=title,
            file_name=f'{title}.pdf',
            processing_status=status,
        )
        presentation.file_path.save(f'{title}.pdf', ContentFile(b'%PDF-test'), save=True)
        slide = PresentationSlide.objects.create(
            presentation=presentation,
            slide_number=1,
        )
        slide.image_path.save('slide.png', ContentFile(b'png'), save=True)
        Presentation.objects.filter(pk=presentation.pk).update(
            uploaded_at=self.now - timedelta(days=age_days),
        )
        presentation.refresh_from_db()
        return presentation, slide

    def create_session(self, presentation):
        started_at = self.now - timedelta(days=400)
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(started_at),
            started_at=started_at,
            ended_at=started_at + timedelta(hours=1),
        )
        event = SlideEvent.objects.create(
            session=session,
            slide=presentation.slides.first(),
            entered_at=started_at,
        )
        return session, event

    def make_records(self):
        old_failed, old_failed_slide = self.presentation(
            'old-failed', status=Presentation.ProcessingStatus.FAILED, age_days=31,
        )
        referenced, referenced_slide = self.presentation(
            'referenced-failed', status=Presentation.ProcessingStatus.FAILED, age_days=31,
        )
        recent_failed, _ = self.presentation(
            'recent-failed', status=Presentation.ProcessingStatus.FAILED, age_days=29,
        )
        old_ready, _ = self.presentation(
            'old-ready', status=Presentation.ProcessingStatus.READY, age_days=400,
        )
        session, event = self.create_session(referenced)

        old_summary = EngagementSummary.objects.create(
            event=event,
            average_confidence='75.00',
            captured_at=self.now - timedelta(days=181),
        )
        recent_summary = EngagementSummary.objects.create(
            event=event,
            average_confidence='80.00',
            captured_at=self.now - timedelta(days=179),
        )

        old_report_path = default_storage.save('reports/old.pdf', ContentFile(b'old report'))
        recent_report_path = default_storage.save('reports/recent.pdf', ContentFile(b'recent report'))
        old_report = Report.objects.create(
            session=session,
            generated_by=self.teacher,
            report_type='pdf',
            report_path=old_report_path,
        )
        recent_report = Report.objects.create(
            session=session,
            generated_by=self.teacher,
            report_type='pdf',
            report_path=recent_report_path,
        )
        retained_shared_report = Report.objects.create(
            session=session,
            generated_by=self.teacher,
            report_type='pdf',
            report_path=old_report_path,
        )
        Report.objects.filter(pk=old_report.pk).update(
            generated_at=self.now - timedelta(days=366),
        )
        Report.objects.filter(pk=recent_report.pk).update(
            generated_at=self.now - timedelta(days=364),
        )

        old_log = SystemLog.objects.create(user=self.teacher, activity='Old activity')
        recent_log = SystemLog.objects.create(user=self.teacher, activity='Recent activity')
        SystemLog.objects.filter(pk=old_log.pk).update(
            logged_at=self.now - timedelta(days=181),
        )
        SystemLog.objects.filter(pk=recent_log.pk).update(
            logged_at=self.now - timedelta(days=179),
        )

        return {
            'old_failed': old_failed,
            'old_failed_slide': old_failed_slide,
            'referenced': referenced,
            'referenced_slide': referenced_slide,
            'recent_failed': recent_failed,
            'old_ready': old_ready,
            'old_summary': old_summary,
            'recent_summary': recent_summary,
            'old_report': old_report,
            'recent_report': recent_report,
            'retained_shared_report': retained_shared_report,
            'old_log': old_log,
            'recent_log': recent_log,
        }

    def test_dry_run_lists_exact_targets_without_deleting_anything(self):
        records = self.make_records()
        output = io.StringIO()

        call_command('cleanup_data', stdout=output)

        text = output.getvalue()
        self.assertIn('DRY RUN', text)
        for key in ('old_failed', 'old_summary', 'old_report', 'old_log'):
            self.assertIn(str(records[key].pk), text)
        self.assertTrue(Presentation.objects.filter(pk=records['old_failed'].pk).exists())
        self.assertTrue(default_storage.exists(records['old_report'].report_path))

    def test_execute_deletes_only_expired_unreferenced_records_and_files(self):
        records = self.make_records()
        presentation_path = records['old_failed'].file_path.name
        slide_path = records['old_failed_slide'].image_path.name
        report_path = records['old_report'].report_path
        referenced_path = records['referenced'].file_path.name
        referenced_slide_path = records['referenced_slide'].image_path.name

        call_command('cleanup_data', '--execute', stdout=io.StringIO())

        self.assertFalse(Presentation.objects.filter(pk=records['old_failed'].pk).exists())
        self.assertFalse(default_storage.exists(presentation_path))
        self.assertFalse(default_storage.exists(slide_path))
        self.assertFalse(Report.objects.filter(pk=records['old_report'].pk).exists())
        self.assertTrue(default_storage.exists(report_path))
        self.assertFalse(EngagementSummary.objects.filter(pk=records['old_summary'].pk).exists())
        self.assertFalse(SystemLog.objects.filter(pk=records['old_log'].pk).exists())

        for key in ('referenced', 'recent_failed', 'old_ready'):
            self.assertTrue(Presentation.objects.filter(pk=records[key].pk).exists())
        self.assertTrue(default_storage.exists(referenced_path))
        self.assertTrue(default_storage.exists(referenced_slide_path))
        self.assertTrue(Report.objects.filter(pk=records['recent_report'].pk).exists())
        self.assertTrue(Report.objects.filter(pk=records['retained_shared_report'].pk).exists())
        self.assertTrue(EngagementSummary.objects.filter(pk=records['recent_summary'].pk).exists())
        self.assertTrue(SystemLog.objects.filter(pk=records['recent_log'].pk).exists())
