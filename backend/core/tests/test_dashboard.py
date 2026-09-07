from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Camera,
    Classroom,
    ClassroomSession,
    EngagementAlert,
    EngagementSummary,
    Organization,
    Presentation,
    PresentationSlide,
    SlideEvent,
    Subject,
)


User = get_user_model()


class DashboardTests(TestCase):
    password = 'A-strong-dashboard-password-2026'

    def setUp(self):
        self.today = timezone.localdate()
        self.now = timezone.now()
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
            email='system@example.com',
            password=self.password,
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='org.admin',
            email='org.admin@example.com',
            password=self.password,
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            email='teacher.one@example.com',
            first_name='Teacher',
            last_name='One',
            password=self.password,
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='teacher.other',
            email='teacher.other@example.com',
            password=self.password,
            organization=self.other_organization,
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-101',
            capacity=40,
        )
        self.other_classroom = Classroom.objects.create(
            organization=self.other_organization,
            room_code='ROOM-201',
            capacity=30,
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
        Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position=Camera.Position.FRONT,
        )
        Camera.objects.create(
            classroom=self.other_classroom,
            camera_name='Other Front Camera',
            position=Camera.Position.FRONT,
        )
        self.presentation = Presentation.objects.create(
            user=self.teacher,
            title='Data Structures Lecture',
            file_name='data-structures.pptx',
            file_path='/presentations/data-structures.pptx',
            total_slides=10,
        )
        self.other_presentation = Presentation.objects.create(
            user=self.other_teacher,
            title='Networks Lecture',
            file_name='networks.pptx',
            file_path='/presentations/networks.pptx',
            total_slides=8,
        )
        self.session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=self.presentation,
            session_date=self.today,
            started_at=self.now - timedelta(minutes=60),
            ended_at=self.now,
        )
        self.other_session = ClassroomSession.objects.create(
            user=self.other_teacher,
            subject=self.other_subject,
            presentation=self.other_presentation,
            session_date=self.today,
            started_at=self.now - timedelta(minutes=30),
        )
        self.url = reverse('dashboard-summary')

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, (401, 403))

    def test_system_admin_dashboard_counts_all_accessible_records(self):
        self.client.force_login(self.system_admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['counts'], {
            'classrooms': 2,
            'subjects': 2,
            'cameras': 2,
            'sessions_today': 2,
        })
        self.assertEqual(
            {item['id'] for item in response.json()['recent_sessions']},
            {self.session.pk, self.other_session.pk},
        )

    def test_organization_admin_dashboard_is_limited_to_organization(self):
        self.client.force_login(self.org_admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['counts'], {
            'classrooms': 1,
            'subjects': 1,
            'cameras': 1,
            'sessions_today': 1,
        })
        self.assertEqual(
            [item['id'] for item in response.json()['recent_sessions']],
            [self.session.pk],
        )

    def test_teacher_dashboard_contains_only_assigned_and_owned_data(self):
        second_classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-102',
        )
        Subject.objects.create(
            classroom=second_classroom,
            teacher=self.teacher,
            subject_code='IT-302',
            subject_name='Algorithms',
        )
        self.client.force_login(self.teacher)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['counts'], {
            'classrooms': 2,
            'subjects': 2,
            'cameras': 1,
            'sessions_today': 1,
        })
        self.assertEqual(
            [item['id'] for item in response.json()['recent_sessions']],
            [self.session.pk],
        )

    def test_recent_session_uses_real_duration_and_status(self):
        self.client.force_login(self.teacher)

        session = self.client.get(self.url).json()['recent_sessions'][0]

        self.assertEqual(session['subject_name'], self.subject.subject_name)
        self.assertEqual(session['subject_code'], self.subject.subject_code)
        self.assertEqual(session['classroom'], self.classroom.room_code)
        self.assertEqual(session['duration_minutes'], 60)
        self.assertEqual(session['status'], 'completed')
        self.assertIsNone(session['average_engagement'])

    def test_dashboard_reports_no_engagement_data_instead_of_fake_values(self):
        self.client.force_login(self.teacher)

        response = self.client.get(self.url)

        self.assertEqual(response.json()['engagement'], {
            'has_data': False,
            'total_detected': 0,
            'average_score': None,
            'distribution': {
                'engaged': 0,
                'attentive': 0,
                'confused': 0,
                'bored': 0,
                'disengaged': 0,
            },
        })
        self.assertEqual(response.json()['alerts_today'], 0)

    def test_dashboard_aggregates_real_engagement_and_alert_data(self):
        slide = PresentationSlide.objects.create(
            presentation=self.presentation,
            slide_number=1,
            slide_title='Introduction',
        )
        event = SlideEvent.objects.create(
            session=self.session,
            slide=slide,
            entered_at=self.now - timedelta(minutes=45),
        )
        summary = EngagementSummary.objects.create(
            event=event,
            engaged_count=6,
            attentive_count=2,
            confused_count=1,
            bored_count=1,
            disengaged_count=0,
            total_detected=10,
            average_confidence=Decimal('91.50'),
        )
        EngagementAlert.objects.create(
            summary=summary,
            alert_type='disengagement',
            alert_message='Engagement dropped.',
        )
        self.client.force_login(self.teacher)

        data = self.client.get(self.url).json()

        self.assertEqual(data['engagement'], {
            'has_data': True,
            'total_detected': 10,
            'average_score': 80,
            'distribution': {
                'engaged': 60,
                'attentive': 20,
                'confused': 10,
                'bored': 10,
                'disengaged': 0,
            },
        })
        self.assertEqual(data['alerts_today'], 1)
        self.assertEqual(data['recent_sessions'][0]['average_engagement'], 80)
