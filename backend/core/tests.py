from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from .models import Organization, SystemLog


class RegistrationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
        )
        self.url = reverse('register')
        self.payload = {
            'username': 'teacher.one',
            'email': 'teacher@example.com',
            'first_name': 'Teacher',
            'last_name': 'One',
            'middle_name': 'Sample',
            'contact_no': '+639171234567',
            'organization_code': self.organization.organization_code,
            'password': 'A-strong-classroom-passphrase-2026',
            'password_confirmation': 'A-strong-classroom-passphrase-2026',
        }

    def test_registration_creates_teacher_without_logging_them_in(self):
        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username='teacher.one')
        self.assertEqual(user.email, 'teacher@example.com')
        self.assertEqual(user.organization, self.organization)
        self.assertEqual(user.role, get_user_model().Role.TEACHER)
        self.assertEqual(user.status, get_user_model().Status.ACTIVE)
        self.assertTrue(user.check_password(self.payload['password']))
        self.assertNotEqual(user.password, self.payload['password'])
        self.assertNotIn('password', response.json())
        self.assertNotIn('password_confirmation', response.json())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_rejects_duplicate_username(self):
        get_user_model().objects.create_user(
            username=self.payload['username'],
            email='another@example.com',
            password='Existing-password-2026',
        )

        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json())

    def test_registration_rejects_duplicate_username_case_insensitively(self):
        get_user_model().objects.create_user(
            username=self.payload['username'].upper(),
            email='another@example.com',
            password='Existing-password-2026',
        )

        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json())

    def test_database_rejects_duplicate_username_case_insensitively(self):
        get_user_model().objects.create_user(
            username=self.payload['username'],
            email='first@example.com',
            password='Existing-password-2026',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user(
                username=self.payload['username'].upper(),
                email='second@example.com',
                password='Existing-password-2026',
            )

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        get_user_model().objects.create_user(
            username='another.teacher',
            email='TEACHER@example.com',
            password='Existing-password-2026',
        )

        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())

    def test_database_rejects_duplicate_nonempty_email_case_insensitively(self):
        get_user_model().objects.create_user(
            username='first.teacher',
            email='teacher@example.com',
            password='Existing-password-2026',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user(
                username='second.teacher',
                email='TEACHER@example.com',
                password='Existing-password-2026',
            )

    def test_registration_rejects_unknown_organization(self):
        self.payload['organization_code'] = 'UNKNOWN'

        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('organization_code', response.json())

    def test_registration_rejects_inactive_organization(self):
        self.organization.status = Organization.Status.INACTIVE
        self.organization.save(update_fields=['status'])

        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('organization_code', response.json())

    def test_registration_rejects_password_mismatch(self):
        self.payload['password_confirmation'] = 'A-different-passphrase-2026'

        response = self.client.post(self.url, self.payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirmation', response.json())
        self.assertFalse(get_user_model().objects.filter(username='teacher.one').exists())

    def test_registration_applies_django_password_policy(self):
        invalid_passwords = (
            'Short!12345',
            '1234567890123456',
            'teacher.one-2026',
            'password123456',
        )

        for password in invalid_passwords:
            with self.subTest(password=password):
                payload = {
                    **self.payload,
                    'password': password,
                    'password_confirmation': password,
                }
                response = self.client.post(self.url, payload, content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('password', response.json())

    def test_registration_requires_identity_and_password_fields(self):
        required_fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'organization_code',
            'password',
            'password_confirmation',
        )

        for field in required_fields:
            with self.subTest(field=field):
                payload = {**self.payload}
                payload.pop(field)
                response = self.client.post(self.url, payload, content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())

    def test_registration_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        missing_token = csrf_client.post(
            self.url,
            self.payload,
            content_type='application/json',
        )
        self.assertEqual(missing_token.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username='teacher.one').exists())

        csrf_client.get(reverse('csrf'))
        response = csrf_client.post(
            self.url,
            self.payload,
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_client.cookies['csrftoken'].value,
            HTTP_ORIGIN='http://localhost:5173',
        )
        self.assertEqual(response.status_code, 201)


class SessionAuthenticationTests(TestCase):
    password = 'A-strong-session-password-2026'

    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
        )
        self.user = get_user_model().objects.create_user(
            username='teacher.one',
            email='teacher@example.com',
            first_name='Teacher',
            last_name='One',
            organization=self.organization,
            password=self.password,
        )
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.me_url = reverse('current-user')
        self.csrf_url = reverse('csrf')

    def test_login_with_email_creates_session_and_returns_user(self):
        response = self.client.post(
            self.login_url,
            {'identity': self.user.email, 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['username'], self.user.username)
        self.assertEqual(response.json()['email'], self.user.email)
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))
        self.assertTrue(response.cookies['sessionid']['httponly'])
        self.assertEqual(response.cookies['sessionid']['samesite'], 'Lax')
        self.assertTrue(response.cookies['sessionid']['secure'])

    def test_login_accepts_username_case_insensitively(self):
        response = self.client.post(
            self.login_url,
            {'identity': self.user.username.upper(), 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))

    def test_login_rejects_invalid_credentials_without_account_disclosure(self):
        wrong_password = self.client.post(
            self.login_url,
            {'identity': self.user.email, 'password': 'wrong-password'},
            content_type='application/json',
        )
        unknown_user = self.client.post(
            self.login_url,
            {'identity': 'unknown@example.com', 'password': 'wrong-password'},
            content_type='application/json',
        )

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(wrong_password.json(), unknown_user.json())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rejects_django_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        response = self.client.post(
            self.login_url,
            {'identity': self.user.email, 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rejects_business_inactive_user(self):
        self.user.status = get_user_model().Status.INACTIVE
        self.user.save(update_fields=['status'])

        response = self.client.post(
            self.login_url,
            {'identity': self.user.email, 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rejects_user_from_inactive_organization(self):
        self.organization.status = Organization.Status.INACTIVE
        self.organization.save(update_fields=['status'])

        response = self.client.post(
            self.login_url,
            {'identity': self.user.email, 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_current_user_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertIn(response.status_code, (401, 403))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_existing_session_is_destroyed_after_organization_becomes_inactive(self):
        self.client.force_login(self.user)
        self.organization.status = Organization.Status.INACTIVE
        self.organization.save(update_fields=['status'])

        response = self.client.get(self.me_url)

        self.assertIn(response.status_code, (401, 403))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rotates_existing_session_key(self):
        session = self.client.session
        session['anonymous-data'] = True
        session.save()
        original_session_key = session.session_key

        response = self.client.post(
            self.login_url,
            {'identity': self.user.email, 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.client.session.session_key, original_session_key)

    def test_current_user_returns_authenticated_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], self.user.pk)
        self.assertNotIn('password', response.json())

    def test_existing_session_is_rejected_after_user_becomes_inactive(self):
        self.client.force_login(self.user)
        self.user.status = get_user_model().Status.INACTIVE
        self.user.save(update_fields=['status'])

        response = self.client.get(self.me_url)

        self.assertIn(response.status_code, (401, 403))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_existing_session_is_destroyed_after_django_deactivation(self):
        self.client.force_login(self.user)
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        response = self.client.get(self.me_url)

        self.assertIn(response.status_code, (401, 403))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_destroys_session_and_blocks_protected_endpoint(self):
        self.client.force_login(self.user)

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 204)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertIn(self.client.get(self.me_url).status_code, (401, 403))

    def test_logout_rejects_get(self):
        self.client.force_login(self.user)

        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_and_logout_require_csrf_tokens(self):
        csrf_client = Client(enforce_csrf_checks=True)
        login_payload = {'identity': self.user.email, 'password': self.password}

        missing_login_token = csrf_client.post(
            self.login_url,
            login_payload,
            content_type='application/json',
        )
        self.assertEqual(missing_login_token.status_code, 403)

        csrf_response = csrf_client.get(self.csrf_url)
        self.assertTrue(csrf_response.cookies['csrftoken']['secure'])
        token = csrf_client.cookies['csrftoken'].value
        login_response = csrf_client.post(
            self.login_url,
            login_payload,
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(login_response.status_code, 200)
        token = csrf_client.cookies['csrftoken'].value

        missing_logout_token = csrf_client.post(self.logout_url)
        self.assertEqual(missing_logout_token.status_code, 403)
        self.assertIn('_auth_user_id', csrf_client.session)

        logout_response = csrf_client.post(
            self.logout_url,
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(logout_response.status_code, 204)
        self.assertNotIn('_auth_user_id', csrf_client.session)

    def test_logout_accepts_vite_fallback_development_origin(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        csrf_client.get(self.csrf_url)

        response = csrf_client.post(
            self.logout_url,
            HTTP_X_CSRFTOKEN=csrf_client.cookies['csrftoken'].value,
            HTTP_ORIGIN='http://localhost:5174',
        )

        self.assertEqual(response.status_code, 204)
        self.assertNotIn('_auth_user_id', csrf_client.session)


class AuthenticationAdminTests(TestCase):
    password = 'A-strong-admin-password-2026'

    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='system.admin',
            email='admin@example.com',
            password=self.password,
            role=get_user_model().Role.SYSTEM_ADMIN,
        )
        self.client.force_login(self.admin_user)

    def test_authenticated_profile_reports_admin_access(self):
        response = self.client.get(reverse('current-user'))

        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()['can_access_admin'], True)

    def test_non_staff_profile_has_no_admin_access(self):
        teacher = get_user_model().objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='A-strong-teacher-password-2026',
        )
        self.client.force_login(teacher)

        response = self.client.get(reverse('current-user'))

        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()['can_access_admin'], False)

    def test_application_login_session_opens_admin_without_second_login(self):
        self.client.logout()
        login_response = self.client.post(
            reverse('login'),
            {'identity': self.admin_user.email, 'password': self.password},
            content_type='application/json',
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertIs(login_response.json()['can_access_admin'], True)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_non_staff_user_is_rejected_by_admin(self):
        teacher = get_user_model().objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='A-strong-teacher-password-2026',
        )
        self.client.force_login(teacher)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)

    def test_admin_can_open_organization_creation_form(self):
        response = self.client.get(reverse('admin:core_organization_add'))

        self.assertEqual(response.status_code, 200)

    def test_admin_can_open_user_creation_form(self):
        response = self.client.get(reverse('admin:core_user_add'))

        self.assertEqual(response.status_code, 200)

    def test_admin_logout_accepts_vite_fallback_development_origin(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin_user)
        csrf_client.get(reverse('admin:index'))

        response = csrf_client.post(
            reverse('admin:logout'),
            HTTP_X_CSRFTOKEN=csrf_client.cookies['csrftoken'].value,
            HTTP_ORIGIN='http://localhost:5174',
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', csrf_client.session)


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
