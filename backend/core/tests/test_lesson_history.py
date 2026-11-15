import csv
import io
from datetime import timedelta
from unittest.mock import patch

import pymupdf
from django.core.files.storage import default_storage
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .test_lesson_continuation import LessonFixtures
from ..analytics import build_session_analytics
from ..models import ClassroomSession, EngagementSummary, Organization, Report, SlideEvent
from ..report_generation import analytics_csv_content


class LessonHistoryTests(LessonFixtures, TestCase):
    def two_meetings(self):
        start = timezone.now().replace(hour=1, minute=0, second=0, microsecond=0)
        with patch('core.session_lifecycle.timezone.now', return_value=start):
            first = self.start()
        for minutes, slide in ((10, self.slides[1]), (25, self.slides[0])):
            first.lesson.refresh_from_db()
            with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(minutes=minutes)):
                moved = self.post('session-enter-slide', {'slide': slide.pk, 'expected_revision': first.lesson.revision}, first.pk)
            self.assertEqual(moved.status_code, 201)
        EngagementSummary.objects.create(
            event=first.slide_events.order_by('entered_at').first(),
            engaged_count=3, total_detected=3, average_confidence=90,
        )
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(minutes=40)):
            self.assertEqual(self.end(first).status_code, 200)
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(days=1, minutes=-5)):
            second = self.continue_lesson(first)
        ClassroomSession.objects.filter(pk=second.pk).update(prepared_at=start + timedelta(days=1, minutes=-5))
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(days=1)):
            self.assertEqual(self.start_prepared(second).status_code, 200)
        EngagementSummary.objects.create(
            event=second.slide_events.get(), attentive_count=5,
            total_detected=5, average_confidence=91,
        )
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(days=1, minutes=40)):
            self.assertEqual(self.end(second, 'finish').status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        return first, second

    def test_history_and_revisited_slides_keep_actual_meeting_boundaries(self):
        first, second = self.two_meetings()
        history = self.client.get(reverse('session-list'), {'lesson': first.lesson_id}).json()
        self.assertEqual([row['id'] for row in history['results']], [first.pk, second.pk])
        self.assertEqual([row['end_action'] for row in history['results']], ['save', 'finish'])
        self.assertEqual(history['results'][1]['continued_from'], first.pk)
        for session, total in ((first, 3), (second, 5)):
            analytics = build_session_analytics(session)
            self.assertEqual(analytics['session']['duration_seconds'], 2400)
            self.assertEqual(sum(row['duration_seconds'] for row in analytics['slides']), 2400)
            self.assertEqual(analytics['summary']['total_detections'], total)
            self.assertEqual(analytics['session']['lesson_state'], 'completed')
            rows = list(csv.DictReader(io.StringIO(analytics_csv_content(analytics))))
            self.assertEqual({row['Class Meeting ID'] for row in rows}, {str(session.pk)})
            self.assertEqual({row['Lesson ID'] for row in rows}, {str(first.lesson_id)})
            self.assertEqual(sum(int(row['Duration Seconds']) for row in rows), 2400)
        self.assertEqual([row['duration_seconds'] for row in build_session_analytics(first)['slides']], [1500, 900])
        self.assertEqual(build_session_analytics(first)['slides'][0]['engaged'], 100)
        self.assertEqual(build_session_analytics(second)['slides'][0]['attentive'], 100)

    def test_legacy_out_of_bounds_events_are_clipped_to_their_meeting(self):
        first, _ = self.two_meetings()
        first.slide_events.order_by('entered_at').filter(slide=self.slides[0]).update(entered_at=first.started_at - timedelta(minutes=5))
        SlideEvent.objects.create(session=first, slide=self.slides[2], entered_at=first.ended_at + timedelta(hours=2))
        analytics = build_session_analytics(first)
        self.assertEqual(sum(row['duration_seconds'] for row in analytics['slides']), 2400)
        self.assertEqual(analytics['slides'][-1]['duration_seconds'], 0)

    def test_saved_reports_survive_continuation_with_unique_names_and_original_bytes(self):
        first = self.start()
        self.end(first)
        snapshots = []
        for report_type in ('pdf', 'csv'):
            response = self.post('report-list-create', {'session': first.pk, 'report_type': report_type})
            self.assertEqual(response.status_code, 201, response.content)
            report = Report.objects.get(pk=response.json()['id'])
            with default_storage.open(report.report_path, 'rb') as stream:
                content = stream.read()
            snapshots.append((report, content, response.json()['file_name']))
            if report_type == 'pdf':
                with pymupdf.open(stream=content, filetype='pdf') as document:
                    text = ''.join(page.get_text() for page in document)
                self.assertIn(f'Class #{first.pk} | Class saved', text)
                self.assertIn(f'Lesson #{first.lesson_id} | saved', text)
        second = self.continue_lesson(first)
        self.start_prepared(second)
        self.end(second, 'finish')
        for report, original, name in snapshots:
            response = self.client.get(reverse('report-download', args=[report.pk]))
            content = b''.join(response.streaming_content)
            response.close()
            self.assertEqual(content, original)
            newer = self.post('report-list-create', {'session': second.pk, 'report_type': report.report_type}).json()
            self.assertNotEqual(newer['file_name'], name)
            self.assertEqual(newer['end_action'], 'finish')
            self.assertEqual(newer['continued_from'], first.pk)
        reports = self.client.get(reverse('report-list-create')).json()['results']
        saved = [row for row in reports if row['session'] == first.pk]
        self.assertTrue(all(row['end_action'] == 'save' and row['lesson_state'] == 'completed' for row in saved))

    def test_history_and_metadata_respect_existing_teacher_and_organization_access(self):
        first, second = self.two_meetings()
        self.client.force_login(self.peer)
        self.assertEqual(self.client.get(reverse('session-list'), {'lesson': first.lesson_id}).json()['count'], 0)
        self.assertEqual(self.client.get(reverse('session-analytics', args=[first.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('session-list'), {'lesson': first.lesson_id}).json()['count'], 2)
        for name in ('analytics-session-list', 'report-options'):
            response = self.client.get(reverse(name)).json()
            self.assertEqual({row['lesson_id'] for row in response['results']}, {first.lesson_id})
        dashboard = self.client.get(reverse('dashboard-summary')).json()['recent_sessions']
        self.assertEqual({row['end_action'] for row in dashboard}, {'save', 'finish'})
        self.admin.organization = Organization.objects.create(organization_name='Other', organization_code='OTHER-HISTORY')
        self.admin.save(update_fields=['organization'])
        self.classroom.organization = self.admin.organization
        self.classroom.save(update_fields=['organization'])
        self.assertEqual(self.client.get(reverse('session-list'), {'lesson': first.lesson_id}).json()['count'], 0)
        self.assertEqual(self.client.get(reverse('dashboard-summary')).json()['recent_sessions'], [])
        self.client.force_login(self.teacher)
        self.assertEqual(len(self.client.get(reverse('dashboard-summary')).json()['recent_sessions']), 2)
        current = ClassroomSession.objects.create(
            user=self.admin, subject=self.subject, presentation=self.presentation,
            session_date=second.session_date, started_at=second.ended_at + timedelta(minutes=1),
            ended_at=second.ended_at + timedelta(minutes=41),
        )
        event = SlideEvent.objects.create(session=current, slide=self.slides[0], entered_at=current.started_at)
        EngagementSummary.objects.create(event=event, engaged_count=1, total_detected=1, average_confidence=90)
        self.client.force_login(self.admin)
        with patch('core.report_generation.build_session_analytics', wraps=build_session_analytics) as build:
            self.assertEqual(self.post('report-list-create', {'session': current.pk, 'report_type': 'csv'}).status_code, 201)
        self.assertIsNone(build.call_args.kwargs['previous_session'])
