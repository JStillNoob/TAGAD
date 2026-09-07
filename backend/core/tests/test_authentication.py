from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Organization, SystemLog


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

