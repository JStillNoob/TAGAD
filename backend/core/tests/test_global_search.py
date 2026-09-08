from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Classroom, ClassroomSession, Organization, Presentation, Subject, User


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Alpha University',
            organization_code='ALPHA',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University',
            organization_code='OTHER',
        )
        self.system_admin = User.objects.create_superuser(
            username='system.search',
            email='system@example.com',
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='alpha.admin',
            email='admin@alpha.example',
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='alpha.teacher',
            email='teacher@alpha.example',
            first_name='Alice',
            last_name='Alpha',
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='other.teacher',
            email='teacher@other.example',
            first_name='Olivia',
            last_name='Other',
            organization=self.other_organization,
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ALPHA-101',
            building='Alpha Hall',
        )
        self.other_classroom = Classroom.objects.create(
            organization=self.other_organization,
            room_code='OTHER-201',
            building='Other Hall',
        )
        self.subject = Subject.objects.create(
            classroom=self.classroom,
            teacher=self.teacher,
            subject_code='ALPHA-IT',
            subject_name='Alpha Computing',
        )
        self.other_subject = Subject.objects.create(
            classroom=self.other_classroom,
            teacher=self.other_teacher,
            subject_code='OTHER-IT',
            subject_name='Other Computing',
        )
        self.presentation = Presentation.objects.create(
            user=self.teacher,
            title='Alpha Lecture',
            file_name='alpha.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
        )
        self.other_presentation = Presentation.objects.create(
            user=self.other_teacher,
            title='Other Lecture',
            file_name='other.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
        )
        now = timezone.now()
        self.session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=self.presentation,
            session_date=timezone.localdate(now),
            started_at=now,
            ended_at=now,
        )
        self.other_session = ClassroomSession.objects.create(
            user=self.other_teacher,
            subject=self.other_subject,
            presentation=self.other_presentation,
            session_date=timezone.localdate(now),
            started_at=now,
            ended_at=now,
        )
        self.url = reverse('global-search')

    def search(self, user, query):
        self.client.force_login(user)
        return self.client.get(self.url, {'q': query})

    def result_keys(self, response):
        return {(item['type'], item['id']) for item in response.json()['results']}

    def test_system_admin_can_search_every_supported_type(self):
        response = self.search(self.system_admin, 'Alpha')
        result_types = {item['type'] for item in response.json()['results']}

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            result_types,
            {'user', 'classroom', 'subject', 'session', 'presentation'},
        )
        for result in response.json()['results']:
            self.assertEqual(set(result), {'type', 'id', 'title', 'subtitle', 'url'})
            self.assertTrue(result['url'].startswith('/'))

    def test_teacher_only_sees_own_scoped_records(self):
        own = self.search(self.teacher, 'Alpha')
        foreign = self.search(self.teacher, 'Other')

        self.assertIn(('user', self.teacher.pk), self.result_keys(own))
        self.assertIn(('classroom', self.classroom.pk), self.result_keys(own))
        self.assertIn(('subject', self.subject.pk), self.result_keys(own))
        self.assertIn(('session', self.session.pk), self.result_keys(own))
        self.assertIn(('presentation', self.presentation.pk), self.result_keys(own))
        self.assertEqual(foreign.json(), {'results': []})

    def test_organization_admin_cannot_see_other_organization(self):
        own = self.search(self.org_admin, 'Alpha')
        foreign = self.search(self.org_admin, 'Other')

        self.assertIn(('user', self.teacher.pk), self.result_keys(own))
        self.assertNotIn(('user', self.system_admin.pk), self.result_keys(own))
        self.assertEqual(foreign.json(), {'results': []})

    def test_short_or_blank_queries_return_no_results(self):
        blank = self.search(self.system_admin, '')
        short = self.search(self.system_admin, 'A')

        self.assertEqual(blank.json(), {'results': []})
        self.assertEqual(short.json(), {'results': []})

    def test_search_requires_authentication(self):
        response = self.client.get(self.url, {'q': 'Alpha'})

        self.assertIn(response.status_code, (401, 403))
