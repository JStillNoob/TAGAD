from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..models import Organization, SystemLog


class AccountSettingsTests(TestCase):
    password = 'A-strong-settings-password-2026!'

    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
            address='Old address',
            contact_email='old@example.com',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University',
            organization_code='OTHER-U',
        )
        User = get_user_model()
        self.system_admin = User.objects.create_superuser(
            username='system.admin',
            email='system@example.com',
            password=self.password,
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='org.admin',
            email='org@example.com',
            password=self.password,
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            email='teacher@example.com',
            first_name='Terry',
            last_name='Teacher',
            password=self.password,
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.settings_url = reverse('account-settings')
        self.profile_url = reverse('profile-settings')
        self.organization_url = reverse('organization-settings')
        self.password_url = reverse('password-settings')

    def test_settings_returns_real_user_and_organization(self):
        self.client.force_login(self.teacher)

        response = self.client.get(self.settings_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'teacher.one')
        self.assertEqual(response.json()['organization']['organization_code'], 'TAGAD-U')
        self.assertFalse(response.json()['can_edit_organization'])

    def test_system_admin_without_organization_receives_null_organization(self):
        self.client.force_login(self.system_admin)

        response = self.client.get(self.settings_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['organization'])
        self.assertFalse(response.json()['can_edit_organization'])

    def test_user_updates_only_editable_profile_fields(self):
        self.client.force_login(self.teacher)

        response = self.client.patch(
            self.profile_url,
            data={
                'first_name': 'Updated',
                'middle_name': 'Middle',
                'last_name': 'Name',
                'email': 'updated@example.com',
                'contact_no': '09171234567',
                'username': 'not-allowed',
                'role': get_user_model().Role.SYSTEM_ADMIN,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.first_name, 'Updated')
        self.assertEqual(self.teacher.username, 'teacher.one')
        self.assertEqual(self.teacher.role, get_user_model().Role.TEACHER)
        self.assertTrue(SystemLog.objects.filter(
            user=self.teacher,
            activity='Updated own profile.',
        ).exists())

    def test_profile_rejects_another_users_email_case_insensitively(self):
        self.client.force_login(self.teacher)

        response = self.client.patch(
            self.profile_url,
            data={'email': 'ORG@EXAMPLE.COM'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())

    def test_org_admin_can_update_contact_details_but_not_identity(self):
        self.client.force_login(self.org_admin)

        response = self.client.patch(
            self.organization_url,
            data={
                'address': 'New address',
                'contact_email': 'contact@example.com',
                'contact_no': '12345',
                'organization_name': 'Not allowed',
                'status': Organization.Status.INACTIVE,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.address, 'New address')
        self.assertEqual(self.organization.organization_name, 'Tagad University')
        self.assertEqual(self.organization.status, Organization.Status.ACTIVE)

    def test_teacher_and_unassigned_system_admin_cannot_edit_organization(self):
        self.client.force_login(self.teacher)
        teacher_response = self.client.patch(
            self.organization_url,
            data={'address': 'No'},
            content_type='application/json',
        )
        self.client.force_login(self.system_admin)
        admin_response = self.client.patch(
            self.organization_url,
            data={'address': 'No'},
            content_type='application/json',
        )

        self.assertEqual(teacher_response.status_code, 403)
        self.assertEqual(admin_response.status_code, 403)

    def test_password_change_validates_current_match_and_policy(self):
        self.client.force_login(self.teacher)

        wrong_current = self.client.post(self.password_url, {
            'current_password': 'wrong',
            'new_password': 'Valid-new-password-2026!',
            'password_confirmation': 'Valid-new-password-2026!',
        })
        mismatch = self.client.post(self.password_url, {
            'current_password': self.password,
            'new_password': 'Valid-new-password-2026!',
            'password_confirmation': 'Different-password-2026!',
        })
        weak = self.client.post(self.password_url, {
            'current_password': self.password,
            'new_password': 'lowercase-only-password',
            'password_confirmation': 'lowercase-only-password',
        })

        self.assertEqual(wrong_current.status_code, 400)
        self.assertIn('current_password', wrong_current.json())
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn('password_confirmation', mismatch.json())
        self.assertEqual(weak.status_code, 400)
        self.assertIn('new_password', weak.json())

    def test_successful_password_change_keeps_session_authenticated(self):
        self.client.force_login(self.teacher)
        new_password = 'Valid-new-password-2026!'

        response = self.client.post(self.password_url, {
            'current_password': self.password,
            'new_password': new_password,
            'password_confirmation': new_password,
        })
        current_user = self.client.get(reverse('current-user'))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(current_user.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password(new_password))
        self.assertTrue(SystemLog.objects.filter(
            user=self.teacher,
            activity='Changed own password.',
        ).exists())
