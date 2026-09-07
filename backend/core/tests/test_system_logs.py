from datetime import datetime, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Organization, SystemLog


class SystemLogTests(TestCase):
    password = 'A-strong-log-password-2026'

    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University',
            organization_code='OTHER-U',
        )
        User = get_user_model()
        self.system_admin = User.objects.create_superuser(
            username='system.admin',
            password=self.password,
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='org.admin',
            first_name='Olivia',
            last_name='Admin',
            password=self.password,
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            first_name='Terry',
            last_name='Teacher',
            password=self.password,
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='teacher.other',
            password=self.password,
            organization=self.other_organization,
            role=User.Role.TEACHER,
        )
        self.system_log = SystemLog.objects.create(
            user=self.system_admin,
            activity='Changed a global setting.',
            ip_address='10.0.0.1',
        )
        self.org_log = SystemLog.objects.create(
            user=self.org_admin,
            activity='Created a teacher account.',
            ip_address='10.0.0.2',
        )
        self.teacher_log = SystemLog.objects.create(
            user=self.teacher,
            activity='Uploaded a presentation.',
            ip_address='10.0.0.3',
        )
        self.other_log = SystemLog.objects.create(
            user=self.other_teacher,
            activity='Started another session.',
            ip_address='10.0.0.4',
        )
        self.url = reverse('system-log-list')

    def test_anonymous_user_cannot_access_logs(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, (401, 403))

    def test_system_admin_sees_all_logs_newest_first(self):
        self.client.force_login(self.system_admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 4)
        self.assertEqual(
            [item['id'] for item in payload['results']],
            [self.other_log.pk, self.teacher_log.pk, self.org_log.pk, self.system_log.pk],
        )
        self.assertEqual(payload['results'][1]['user_name'], 'Terry Teacher')

    def test_org_admin_sees_only_organization_logs(self):
        self.client.force_login(self.org_admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['id'] for item in response.json()['results']},
            {self.org_log.pk, self.teacher_log.pk},
        )

    def test_teacher_sees_only_own_logs(self):
        self.client.force_login(self.teacher)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['id'] for item in response.json()['results']],
            [self.teacher_log.pk],
        )

    def test_search_matches_user_activity_and_ip_address(self):
        self.client.force_login(self.system_admin)

        by_user = self.client.get(self.url, {'search': 'Terry'}).json()['results']
        by_activity = self.client.get(self.url, {'search': 'teacher account'}).json()['results']
        by_ip = self.client.get(self.url, {'search': '10.0.0.4'}).json()['results']

        self.assertEqual([item['id'] for item in by_user], [self.teacher_log.pk])
        self.assertEqual([item['id'] for item in by_activity], [self.org_log.pk])
        self.assertEqual([item['id'] for item in by_ip], [self.other_log.pk])

    def test_date_filters_are_inclusive_and_invalid_dates_are_rejected(self):
        yesterday = timezone.now() - timedelta(days=1)
        SystemLog.objects.filter(pk=self.system_log.pk).update(logged_at=yesterday)
        self.client.force_login(self.system_admin)

        today = timezone.localdate().isoformat()
        response = self.client.get(self.url, {'date_from': today, 'date_to': today})
        invalid = self.client.get(self.url, {'date_from': 'not-a-date'})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.system_log.pk, {item['id'] for item in response.json()['results']})
        self.assertEqual(invalid.status_code, 400)

    def test_date_filter_uses_philippine_local_date_near_utc_midnight(self):
        SystemLog.objects.filter(pk=self.teacher_log.pk).update(
            logged_at=datetime(2026, 9, 7, 16, 30, tzinfo=datetime_timezone.utc),
        )
        self.client.force_login(self.teacher)

        response = self.client.get(self.url, {
            'date_from': '2026-09-08',
            'date_to': '2026-09-08',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['id'] for item in response.json()['results']],
            [self.teacher_log.pk],
        )

    def test_results_are_paginated(self):
        SystemLog.objects.bulk_create([
            SystemLog(user=self.teacher, activity=f'Activity {number}.')
            for number in range(21)
        ])
        self.client.force_login(self.system_admin)

        first_page = self.client.get(self.url).json()
        second_page = self.client.get(self.url, {'page': 2}).json()

        self.assertEqual(first_page['count'], 25)
        self.assertEqual(len(first_page['results']), 20)
        self.assertEqual(len(second_page['results']), 5)

    def test_login_and_logout_create_activity_logs(self):
        login_response = self.client.post(reverse('login'), {
            'identity': self.teacher.username,
            'password': self.password,
        })
        logout_response = self.client.post(reverse('logout'))

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(logout_response.status_code, 204)
        self.assertTrue(SystemLog.objects.filter(user=self.teacher, activity='Logged in.').exists())
        self.assertTrue(SystemLog.objects.filter(user=self.teacher, activity='Logged out.').exists())
