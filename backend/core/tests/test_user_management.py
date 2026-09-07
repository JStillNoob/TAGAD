from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Organization, SystemLog
class UserManagementTests(TestCase):
    password = 'A-strong-managed-password-2026'

    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University',
            organization_code='OTHER-U',
        )
        self.system_admin = get_user_model().objects.create_superuser(
            username='system.admin',
            email='system@example.com',
            password=self.password,
            role=get_user_model().Role.SYSTEM_ADMIN,
        )
        self.org_admin = get_user_model().objects.create_user(
            username='org.admin',
            email='org.admin@example.com',
            password=self.password,
            organization=self.organization,
            role=get_user_model().Role.ORG_ADMIN,
        )
        self.teacher = get_user_model().objects.create_user(
            username='teacher.one',
            email='teacher.one@example.com',
            password=self.password,
            organization=self.organization,
            role=get_user_model().Role.TEACHER,
        )
        self.other_teacher = get_user_model().objects.create_user(
            username='teacher.other',
            email='teacher.other@example.com',
            password=self.password,
            organization=self.other_organization,
            role=get_user_model().Role.TEACHER,
        )
        self.list_url = reverse('user-list')

    def user_payload(self, **overrides):
        payload = {
            'username': 'managed.teacher',
            'email': 'managed.teacher@example.com',
            'first_name': 'Managed',
            'middle_name': '',
            'last_name': 'Teacher',
            'contact_no': '+639171234567',
            'organization': self.organization.pk,
            'role': get_user_model().Role.TEACHER,
            'status': get_user_model().Status.ACTIVE,
            'password': self.password,
        }
        payload.update(overrides)
        return payload

    def test_project_defines_the_three_documented_roles(self):
        self.assertEqual(
            set(get_user_model().Role.values),
            {'system_admin', 'org_admin', 'teacher'},
        )

    def test_system_admin_can_list_users_across_organizations(self):
        self.client.force_login(self.system_admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['id'] for item in response.json()},
            {
                self.system_admin.pk,
                self.org_admin.pk,
                self.teacher.pk,
                self.other_teacher.pk,
            },
        )

    def test_org_admin_lists_only_teachers_in_their_organization(self):
        self.client.force_login(self.org_admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [self.teacher.pk])

    def test_teacher_and_anonymous_user_cannot_access_user_management(self):
        self.client.force_login(self.teacher)

        teacher_response = self.client.get(self.list_url)
        self.client.logout()
        anonymous_response = self.client.get(self.list_url)

        self.assertEqual(teacher_response.status_code, 403)
        self.assertIn(anonymous_response.status_code, (401, 403))

    def test_system_admin_creates_hashed_org_admin_and_audit_log(self):
        self.client.force_login(self.system_admin)

        response = self.client.post(
            self.list_url,
            self.user_payload(
                username='new.org.admin',
                email='new.org.admin@example.com',
                role=get_user_model().Role.ORG_ADMIN,
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        created = get_user_model().objects.get(username='new.org.admin')
        self.assertTrue(created.check_password(self.password))
        self.assertNotEqual(created.password, self.password)
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertEqual(response.json()['id'], created.pk)
        self.assertEqual(response.json()['organization_name'], self.organization.organization_name)
        self.assertTrue(SystemLog.objects.filter(
            user=self.system_admin,
            activity__contains='Created user account',
        ).exists())
        self.assertNotIn('password', response.json())

    def test_org_admin_can_only_create_teacher_in_own_organization(self):
        self.client.force_login(self.org_admin)

        allowed = self.client.post(
            self.list_url,
            self.user_payload(organization=self.organization.pk),
            content_type='application/json',
        )
        forbidden_role = self.client.post(
            self.list_url,
            self.user_payload(
                username='forbidden.admin',
                email='forbidden.admin@example.com',
                role=get_user_model().Role.ORG_ADMIN,
            ),
            content_type='application/json',
        )
        forbidden_organization = self.client.post(
            self.list_url,
            self.user_payload(
                username='foreign.teacher',
                email='foreign.teacher@example.com',
                organization=self.other_organization.pk,
            ),
            content_type='application/json',
        )

        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.json()['organization'], self.organization.pk)
        self.assertEqual(forbidden_role.status_code, 400)
        self.assertIn('role', forbidden_role.json())
        self.assertEqual(forbidden_organization.status_code, 400)
        self.assertIn('organization', forbidden_organization.json())

    def test_managed_user_validation_requires_org_and_unique_identity(self):
        self.client.force_login(self.system_admin)

        missing_org = self.client.post(
            self.list_url,
            self.user_payload(organization=None),
            content_type='application/json',
        )
        duplicate_username = self.client.post(
            self.list_url,
            self.user_payload(
                username=self.teacher.username.upper(),
                email='unique@example.com',
            ),
            content_type='application/json',
        )
        duplicate_email = self.client.post(
            self.list_url,
            self.user_payload(
                username='unique.teacher',
                email=self.teacher.email.upper(),
            ),
            content_type='application/json',
        )

        self.assertEqual(missing_org.status_code, 400)
        self.assertIn('organization', missing_org.json())
        self.assertEqual(duplicate_username.status_code, 400)
        self.assertIn('username', duplicate_username.json())
        self.assertEqual(duplicate_email.status_code, 400)
        self.assertIn('email', duplicate_email.json())

    def test_system_admin_can_update_user_and_password(self):
        self.client.force_login(self.system_admin)
        new_password = 'Another-strong-managed-password-2026'

        response = self.client.patch(
            reverse('user-detail', args=[self.teacher.pk]),
            {
                'first_name': 'Updated',
                'role': get_user_model().Role.ORG_ADMIN,
                'password': new_password,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.first_name, 'Updated')
        self.assertEqual(self.teacher.role, get_user_model().Role.ORG_ADMIN)
        self.assertTrue(self.teacher.check_password(new_password))
        self.assertTrue(SystemLog.objects.filter(
            user=self.system_admin,
            activity__contains='Updated user account',
        ).exists())

    def test_org_admin_cannot_manage_admin_or_foreign_teacher(self):
        self.client.force_login(self.org_admin)

        admin_response = self.client.patch(
            reverse('user-detail', args=[self.system_admin.pk]),
            {'first_name': 'Nope'},
            content_type='application/json',
        )
        foreign_response = self.client.patch(
            reverse('user-detail', args=[self.other_teacher.pk]),
            {'first_name': 'Nope'},
            content_type='application/json',
        )

        self.assertEqual(admin_response.status_code, 404)
        self.assertEqual(foreign_response.status_code, 404)

    def test_admin_cannot_change_own_role_status_or_organization(self):
        self.client.force_login(self.system_admin)

        response = self.client.patch(
            reverse('user-detail', args=[self.system_admin.pk]),
            {
                'role': get_user_model().Role.TEACHER,
                'status': get_user_model().Status.INACTIVE,
                'organization': self.organization.pk,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('role', response.json())
        self.assertIn('status', response.json())
        self.assertIn('organization', response.json())

    def test_delete_deactivates_account_without_removing_it(self):
        self.client.force_login(self.system_admin)

        response = self.client.delete(reverse('user-detail', args=[self.teacher.pk]))

        self.assertEqual(response.status_code, 204)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.status, get_user_model().Status.INACTIVE)
        self.assertFalse(self.teacher.is_active)
        self.assertTrue(SystemLog.objects.filter(
            user=self.system_admin,
            activity__contains='Deactivated user account',
        ).exists())

    def test_status_update_reactivates_account_and_logs_it(self):
        self.teacher.status = get_user_model().Status.INACTIVE
        self.teacher.is_active = False
        self.teacher.save(update_fields=['status', 'is_active'])
        self.client.force_login(self.system_admin)

        response = self.client.patch(
            reverse('user-detail', args=[self.teacher.pk]),
            {'status': get_user_model().Status.ACTIVE},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_active)
        self.assertTrue(SystemLog.objects.filter(
            user=self.system_admin,
            activity__contains='Reactivated user account',
        ).exists())

    def test_system_admin_cannot_deactivate_self(self):
        self.client.force_login(self.system_admin)

        response = self.client.delete(reverse('user-detail', args=[self.system_admin.pk]))

        self.assertEqual(response.status_code, 400)
        self.system_admin.refresh_from_db()
        self.assertTrue(self.system_admin.is_active)

    def test_unsafe_user_management_requests_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.system_admin)

        missing_token = csrf_client.post(
            self.list_url,
            self.user_payload(),
            content_type='application/json',
        )

        self.assertEqual(missing_token.status_code, 403)

    def test_user_options_are_scoped_to_the_administrator(self):
        self.client.force_login(self.system_admin)
        system_options = self.client.get(reverse('user-options')).json()

        self.client.force_login(self.org_admin)
        org_options = self.client.get(reverse('user-options')).json()

        self.assertEqual(
            {item['value'] for item in system_options['roles']},
            set(get_user_model().Role.values),
        )
        self.assertEqual(
            {item['id'] for item in system_options['organizations']},
            {self.organization.pk, self.other_organization.pk},
        )
        self.assertEqual(org_options['roles'], [
            {'value': get_user_model().Role.TEACHER, 'label': 'Teacher'},
        ])
        self.assertEqual(org_options['organizations'], [{
            'id': self.organization.pk,
            'name': self.organization.organization_name,
        }])

