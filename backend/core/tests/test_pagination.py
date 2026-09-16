from datetime import timedelta
from time import perf_counter

from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from ..models import Classroom, ClassroomSession, Organization, Presentation, Report, Subject, User
from ..session_serializers import ClassroomSessionSerializer


class GrowingListPaginationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Own University', organization_code='OWN-U',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University', organization_code='OTHER-U',
        )
        self.admin = User.objects.create_user(
            username='own.admin', organization=self.organization, role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='own.teacher', organization=self.organization, role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='other.teacher', organization=self.other_organization, role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization, room_code='OWN-101',
        )
        self.other_classroom = Classroom.objects.create(
            organization=self.other_organization, room_code='OTHER-101',
        )
        self.subject = Subject.objects.create(
            classroom=self.classroom, teacher=self.teacher,
            subject_code='OWN-1', subject_name='Own Subject',
        )
        self.other_subject = Subject.objects.create(
            classroom=self.other_classroom, teacher=self.other_teacher,
            subject_code='OTHER-1', subject_name='Other Subject',
        )
        self.own_presentation = self.make_presentation(self.teacher, 'Own Presentation')
        self.other_presentation = self.make_presentation(self.other_teacher, 'Other Presentation')
        self.own_session = self.make_session(self.teacher, self.subject, self.own_presentation)
        self.other_session = self.make_session(
            self.other_teacher, self.other_subject, self.other_presentation,
        )
        self.own_report = Report.objects.create(
            session=self.own_session, generated_by=self.teacher,
            report_type='pdf', report_path='reports/own.pdf',
        )
        Report.objects.create(
            session=self.other_session, generated_by=self.other_teacher,
            report_type='pdf', report_path='reports/other.pdf',
        )
        self.client.force_login(self.admin)

    def make_presentation(self, user, title):
        return Presentation.objects.create(
            user=user, title=title, file_name='lecture.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
        )

    def make_session(self, user, subject, presentation):
        started_at = timezone.now() - timedelta(hours=1)
        return ClassroomSession.objects.create(
            user=user, subject=subject, presentation=presentation,
            session_date=timezone.localdate(started_at), started_at=started_at,
            ended_at=started_at + timedelta(minutes=45),
        )

    def assert_page_contains_only(self, url, expected_id, **parameters):
        response = self.client.get(url, {'page_size': 1, **parameters})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {'count', 'next', 'previous', 'results'})
        self.assertEqual(payload['count'], 1)
        self.assertEqual([item['id'] for item in payload['results']], [expected_id])

    def test_filtered_pages_preserve_organization_isolation(self):
        self.assert_page_contains_only(
            reverse('user-list'), self.teacher.pk, search='own.teacher',
        )
        self.assert_page_contains_only(
            reverse('classroom-list'), self.classroom.pk, search='OWN-101',
        )
        self.assert_page_contains_only(
            reverse('subject-list'), self.subject.pk, search='Own Subject',
        )
        self.assert_page_contains_only(
            reverse('presentation-list'), self.own_presentation.pk, search='Own Presentation',
        )
        self.assert_page_contains_only(
            reverse('session-list'), self.own_session.pk, search='Own Subject',
        )
        self.assert_page_contains_only(
            reverse('report-list-create'), self.own_report.pk, search='Own Subject',
        )

    def test_invalid_page_size_is_bounded_to_default(self):
        response = self.client.get(reverse('classroom-list'), {'page_size': 10000})

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.json()['results']), 100)

    def test_presentation_and_session_page_queries_stay_bounded(self):
        for number in range(120):
            presentation = self.make_presentation(self.teacher, f'Lecture {number:02d}')
            self.make_session(self.teacher, self.subject, presentation)

        legacy_sessions = (
            ClassroomSession.objects.filter(
                subject__classroom__organization=self.organization,
            )
            .select_related('user', 'subject', 'subject__classroom', 'presentation')
            .prefetch_related(
                'session_cameras__camera', 'presentation__slides', 'slide_events',
            )
            .order_by('-started_at')[:20]
        )
        started_at = perf_counter()
        with CaptureQueriesContext(connection) as legacy_session_queries:
            ClassroomSessionSerializer(legacy_sessions, many=True).data
        legacy_session_elapsed = perf_counter() - started_at

        started_at = perf_counter()
        with CaptureQueriesContext(connection) as presentation_queries:
            presentation_response = self.client.get(
                reverse('presentation-list'), {'page_size': 20},
            )
        presentation_elapsed = perf_counter() - started_at
        started_at = perf_counter()
        with CaptureQueriesContext(connection) as session_queries:
            session_response = self.client.get(reverse('session-list'), {'page_size': 20})
        session_elapsed = perf_counter() - started_at

        self.assertEqual(len(presentation_response.json()['results']), 20)
        self.assertEqual(len(session_response.json()['results']), 20)
        self.assertLessEqual(len(presentation_queries), 8)
        self.assertLessEqual(
            len(session_queries),
            10,
            '\n'.join(query['sql'] for query in session_queries.captured_queries),
        )
        self.assertLess(presentation_elapsed, 1.0)
        self.assertLess(session_elapsed, 1.0)
        self.assertGreater(len(legacy_session_queries), len(session_queries))
        self.assertGreater(legacy_session_elapsed, 0)

    def test_user_classroom_and_report_pages_stay_bounded_at_scale(self):
        User.objects.bulk_create([
            User(
                username=f'scale.teacher.{number:03d}',
                organization=self.organization,
                role=User.Role.TEACHER,
            )
            for number in range(120)
        ])
        Classroom.objects.bulk_create([
            Classroom(
                organization=self.organization,
                room_code=f'SCALE-{number:03d}',
            )
            for number in range(120)
        ])
        Subject.objects.bulk_create([
            Subject(
                classroom=self.classroom,
                teacher=self.teacher,
                subject_code=f'SCALE-SUBJECT-{number:03d}',
                subject_name=f'Scale Subject {number:03d}',
            )
            for number in range(120)
        ])
        Report.objects.bulk_create([
            Report(
                session=self.own_session,
                generated_by=self.teacher,
                report_type='pdf',
                report_path=f'reports/scale-{number:03d}.pdf',
            )
            for number in range(120)
        ])

        for url, query_limit in (
            (reverse('user-list'), 6),
            (reverse('classroom-list'), 8),
            (reverse('subject-list'), 8),
            (reverse('report-list-create'), 6),
        ):
            started_at = perf_counter()
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)
            elapsed = perf_counter() - started_at

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['results']), 20)
            self.assertLessEqual(len(queries), query_limit)
            self.assertLess(elapsed, 1.0)
