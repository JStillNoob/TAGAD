from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Classroom,
    ClassroomSession,
    EngagementSummary,
    Organization,
    Presentation,
    PresentationSlide,
    SlideEvent,
    Subject,
    SystemLog,
    User,
)


class AnalyticsTests(TestCase):
    def setUp(self):
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
        self.colleague = User.objects.create_user(
            username='teacher.two',
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
        self.colleague_subject = Subject.objects.create(
            classroom=self.classroom,
            teacher=self.colleague,
            subject_code='IT-302',
            subject_name='Databases',
        )
        self.other_subject = Subject.objects.create(
            classroom=self.other_classroom,
            teacher=self.other_teacher,
            subject_code='IT-401',
            subject_name='Networks',
        )
        self.presentation = Presentation.objects.create(
            user=self.teacher,
            title='Trees',
            file_name='trees.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
            total_slides=2,
        )
        self.slide_one = PresentationSlide.objects.create(
            presentation=self.presentation,
            slide_number=1,
            slide_title='Introduction to Trees',
        )
        self.slide_two = PresentationSlide.objects.create(
            presentation=self.presentation,
            slide_number=2,
            slide_title='Binary Search Trees',
        )
        self.started_at = timezone.now().replace(microsecond=0) - timedelta(hours=1)
        self.session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=self.presentation,
            session_date=timezone.localdate(),
            started_at=self.started_at,
            ended_at=self.started_at + timedelta(minutes=15),
        )
        self.event_one = SlideEvent.objects.create(
            session=self.session,
            slide=self.slide_one,
            entered_at=self.started_at,
        )
        self.event_two = SlideEvent.objects.create(
            session=self.session,
            slide=self.slide_two,
            entered_at=self.started_at + timedelta(minutes=5),
        )
        self.event_three = SlideEvent.objects.create(
            session=self.session,
            slide=self.slide_one,
            entered_at=self.started_at + timedelta(minutes=10),
        )
        EngagementSummary.objects.create(
            event=self.event_one,
            engaged_count=8,
            attentive_count=1,
            confused_count=1,
            total_detected=10,
            average_confidence='90.00',
        )
        EngagementSummary.objects.create(
            event=self.event_two,
            engaged_count=2,
            attentive_count=1,
            confused_count=6,
            bored_count=1,
            total_detected=10,
            average_confidence='80.00',
        )
        EngagementSummary.objects.create(
            event=self.event_three,
            engaged_count=5,
            attentive_count=3,
            confused_count=1,
            disengaged_count=1,
            total_detected=10,
            average_confidence='100.00',
        )

    def create_session(self, user, subject, *, minutes_ago=120, ended=True):
        presentation = Presentation.objects.create(
            user=user,
            title=f'{subject.subject_code} Slides',
            file_name='slides.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
            total_slides=1,
        )
        slide = PresentationSlide.objects.create(
            presentation=presentation,
            slide_number=1,
            slide_title='Overview',
        )
        started = timezone.now().replace(microsecond=0) - timedelta(minutes=minutes_ago)
        session = ClassroomSession.objects.create(
            user=user,
            subject=subject,
            presentation=presentation,
            session_date=timezone.localdate(started),
            started_at=started,
            ended_at=started + timedelta(minutes=10) if ended else None,
        )
        SlideEvent.objects.create(session=session, slide=slide, entered_at=started)
        return session

    def test_session_list_is_role_scoped_and_includes_ongoing_sessions(self):
        colleague_session = self.create_session(self.colleague, self.colleague_subject)
        foreign_session = self.create_session(self.other_teacher, self.other_subject)
        ongoing = self.create_session(self.teacher, self.subject, minutes_ago=5, ended=False)

        self.client.force_login(self.teacher)
        teacher_ids = [item['id'] for item in self.client.get(reverse('analytics-session-list')).json()]
        self.client.force_login(self.org_admin)
        org_ids = {item['id'] for item in self.client.get(reverse('analytics-session-list')).json()}
        self.client.force_login(self.system_admin)
        system_ids = {item['id'] for item in self.client.get(reverse('analytics-session-list')).json()}

        self.assertEqual(teacher_ids, [ongoing.pk, self.session.pk])
        self.assertEqual(org_ids, {self.session.pk, ongoing.pk, colleague_session.pk})
        self.assertEqual(system_ids, {self.session.pk, ongoing.pk, colleague_session.pk, foreign_session.pk})

    def test_analytics_aggregates_revisited_slides_duration_and_engagement(self):
        previous = self.create_session(self.teacher, self.subject, minutes_ago=180)
        previous_event = previous.slide_events.get()
        EngagementSummary.objects.create(
            event=previous_event,
            engaged_count=4,
            attentive_count=6,
            total_detected=10,
            average_confidence='70.00',
        )
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-analytics', args=[self.session.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['has_data'])
        self.assertEqual(payload['session']['duration_seconds'], 900)
        self.assertEqual(payload['session']['slides_covered'], 2)
        self.assertEqual(payload['summary']['students_detected'], 10)
        self.assertEqual(payload['summary']['total_detections'], 30)
        self.assertEqual(payload['summary']['average_engagement'], 50.0)
        self.assertEqual(payload['summary']['average_confidence'], 90.0)
        self.assertEqual(payload['summary']['engagement_change'], 10.0)
        self.assertEqual(payload['distribution'], {
            'engaged': 50.0,
            'attentive': 16.7,
            'confused': 26.7,
            'bored': 3.3,
            'disengaged': 3.3,
        })
        slides = {item['slide_number']: item for item in payload['slides']}
        self.assertEqual(slides[1]['duration_seconds'], 600)
        self.assertEqual(slides[1]['engaged'], 65.0)
        self.assertEqual(slides[1]['disengaged'], 5.0)
        self.assertEqual(slides[2]['duration_seconds'], 300)
        self.assertEqual(slides[2]['confused'], 60.0)
        self.assertEqual(payload['insights']['highest_engagement']['slide_number'], 1)
        self.assertEqual(payload['insights']['most_confusion']['slide_number'], 2)

    def test_session_without_engagement_returns_truthful_no_data_payload(self):
        empty_session = self.create_session(self.teacher, self.subject)
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-analytics', args=[empty_session.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['has_data'])
        self.assertEqual(payload['summary']['total_detections'], 0)
        self.assertIsNone(payload['summary']['average_engagement'])
        self.assertFalse(payload['slides'][0]['has_data'])
        self.assertIsNone(payload['slides'][0]['engaged'])
        self.assertIsNone(payload['insights'])

    def test_teacher_cannot_access_another_teachers_analytics_or_csv(self):
        foreign_session = self.create_session(self.other_teacher, self.other_subject)
        self.client.force_login(self.teacher)

        detail = self.client.get(reverse('session-analytics', args=[foreign_session.pk]))
        csv_response = self.client.get(reverse('session-analytics-csv', args=[foreign_session.pk]))

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(csv_response.status_code, 404)

    def test_csv_download_contains_real_slide_data_and_is_logged(self):
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-analytics-csv', args=[self.session.pk]))

        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn(f'attachment; filename="analytics-session-{self.session.pk}.csv"', response['Content-Disposition'])
        self.assertIn('Slide,Topic,Timestamp,Duration Seconds,Detected,Engaged %,Attentive %,Confused %,Bored %,Disengaged %,Average Confidence %', content)
        self.assertIn('1,Introduction to Trees', content)
        self.assertIn('2,Binary Search Trees', content)
        self.assertTrue(SystemLog.objects.filter(
            user=self.teacher,
            activity=f'Downloaded analytics CSV for classroom session {self.session.pk}.',
        ).exists())

    def test_analytics_endpoints_require_authentication(self):
        list_response = self.client.get(reverse('analytics-session-list'))
        detail_response = self.client.get(reverse('session-analytics', args=[self.session.pk]))
        csv_response = self.client.get(reverse('session-analytics-csv', args=[self.session.pk]))

        self.assertIn(list_response.status_code, (401, 403))
        self.assertIn(detail_response.status_code, (401, 403))
        self.assertIn(csv_response.status_code, (401, 403))
