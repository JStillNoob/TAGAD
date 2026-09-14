from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.models import Organization, SystemLog, User
from core.request_metadata import request_ip


THROTTLE_TEST_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'tagad-auth-throttle-tests',
    },
}


class ThrottleTestMixin:
    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()


@override_settings(CACHES=THROTTLE_TEST_CACHE)
class LoginThrottleTests(ThrottleTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            organization_name='Throttle School',
            organization_code='THROTTLE',
        )
        self.user = User.objects.create_user(
            username='throttle.teacher',
            email='throttle.teacher@example.com',
            password='SafeThrottle!2026',
            role=User.Role.TEACHER,
            organization=self.organization,
        )
        self.url = reverse('login')

    def sign_in(self, password, ip='198.51.100.10', identity='throttle.teacher'):
        return self.client.post(
            self.url,
            {'identity': identity, 'password': password},
            content_type='application/json',
            REMOTE_ADDR=ip,
        )

    def test_five_failures_are_allowed_then_the_pair_is_temporarily_restricted(self):
        for _ in range(settings.LOGIN_THROTTLE_MAX_FAILURES):
            self.assertEqual(self.sign_in('WrongPassword!9').status_code, 401)

        response = self.sign_in('SafeThrottle!2026')

        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertLessEqual(int(response['Retry-After']), settings.LOGIN_THROTTLE_BLOCK_SECONDS)
        self.assertNotIn('password', response.json()['detail'].lower())
        event = SystemLog.objects.get(
            user=self.user,
            activity='Sign-in temporarily restricted after repeated failed attempts.',
        )
        self.assertEqual(event.ip_address, '198.51.100.10')
        self.assertNotIn('WrongPassword!9', event.activity)
        self.assertNotIn(self.user.username, event.activity)

    def test_successful_login_clears_the_identity_client_failure_state(self):
        for _ in range(settings.LOGIN_THROTTLE_MAX_FAILURES - 1):
            self.assertEqual(self.sign_in('WrongPassword!9').status_code, 401)

        self.assertEqual(self.sign_in('SafeThrottle!2026').status_code, 200)
        self.client.logout()

        for _ in range(settings.LOGIN_THROTTLE_MAX_FAILURES):
            self.assertEqual(self.sign_in('WrongPassword!9').status_code, 401)
        self.assertEqual(self.sign_in('WrongPassword!9').status_code, 429)

    def test_a_restricted_pair_does_not_lock_the_account_on_another_client(self):
        for _ in range(settings.LOGIN_THROTTLE_MAX_FAILURES):
            self.sign_in('WrongPassword!9', ip='198.51.100.10')

        self.assertEqual(
            self.sign_in('SafeThrottle!2026', ip='198.51.100.10').status_code,
            429,
        )
        self.assertEqual(
            self.sign_in('SafeThrottle!2026', ip='198.51.100.11').status_code,
            200,
        )

    @override_settings(LOGIN_THROTTLE_CLIENT_MAX_FAILURES=3)
    def test_client_ceiling_limits_attempts_across_different_identities(self):
        with patch('core.auth_throttling.security_logger.warning') as warning:
            for index in range(3):
                response = self.sign_in(
                    'WrongPassword!9',
                    identity=f'unknown-{index}',
                )
                self.assertEqual(response.status_code, 401)
            response = self.sign_in('WrongPassword!9', identity='another-unknown')

        self.assertEqual(response.status_code, 429)
        self.assertFalse(SystemLog.objects.exists())
        warning.assert_called_once()
        self.assertNotIn('unknown-2', ' '.join(map(str, warning.call_args.args)))
        self.assertNotIn('WrongPassword!9', ' '.join(map(str, warning.call_args.args)))

    def test_restriction_expires_without_disabling_the_account(self):
        with patch('core.auth_throttling.time.time', return_value=1_000):
            for _ in range(settings.LOGIN_THROTTLE_MAX_FAILURES):
                self.sign_in('WrongPassword!9')
            self.assertEqual(self.sign_in('SafeThrottle!2026').status_code, 429)

        with patch(
            'core.auth_throttling.time.time',
            return_value=1_000 + settings.LOGIN_THROTTLE_BLOCK_SECONDS + 1,
        ):
            response = self.sign_in('SafeThrottle!2026')

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)


@override_settings(CACHES=THROTTLE_TEST_CACHE)
class PasswordResetThrottleTests(ThrottleTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            organization_name='Recovery School',
            organization_code='RECOVERY',
        )
        self.user = User.objects.create_user(
            username='recovery.teacher',
            email='recovery.teacher@example.com',
            password='SafeRecovery!2026',
            role=User.Role.TEACHER,
            organization=self.organization,
        )
        self.url = reverse('password-reset-request')

    def request_reset(self, email=None, ip='203.0.113.20'):
        return self.client.post(
            self.url,
            {'email': email or self.user.email},
            content_type='application/json',
            REMOTE_ADDR=ip,
        )

    def test_three_requests_are_sent_then_the_pair_is_temporarily_restricted(self):
        for _ in range(settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS):
            response = self.request_reset()
            self.assertEqual(response.status_code, 200)

        response = self.request_reset()

        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertNotIn(self.user.email, response.json()['detail'])
        throttle_log = SystemLog.objects.get(
            user=self.user,
            activity='Password-reset requests temporarily restricted.',
        )
        self.assertNotIn(self.user.email, throttle_log.activity)
        self.assertNotIn('token', throttle_log.activity.lower())

    def test_unknown_and_known_addresses_receive_the_same_generic_response(self):
        known = self.request_reset(ip='203.0.113.21')
        unknown = self.request_reset(
            email='missing@example.com',
            ip='203.0.113.22',
        )

        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.json(), unknown.json())

    def test_throttled_response_does_not_reveal_whether_an_address_exists(self):
        with patch('core.auth_throttling.security_logger.warning'):
            for _ in range(settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS):
                self.request_reset(ip='203.0.113.23')
            known = self.request_reset(ip='203.0.113.23')

            cache.clear()
            for _ in range(settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS):
                self.request_reset(
                    email='missing@example.com',
                    ip='203.0.113.23',
                )
            unknown = self.request_reset(
                email='missing@example.com',
                ip='203.0.113.23',
            )

        self.assertEqual(known.status_code, 429)
        self.assertEqual(unknown.status_code, 429)
        self.assertEqual(known.json(), unknown.json())

    def test_restricted_address_can_be_requested_from_another_client(self):
        for _ in range(settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS):
            self.request_reset(ip='203.0.113.21')

        self.assertEqual(self.request_reset(ip='203.0.113.21').status_code, 429)
        self.assertEqual(self.request_reset(ip='203.0.113.22').status_code, 200)

    @override_settings(PASSWORD_RESET_THROTTLE_CLIENT_MAX_REQUESTS=2)
    def test_client_ceiling_limits_requests_for_different_addresses(self):
        with patch('core.auth_throttling.security_logger.warning') as warning:
            for index in range(2):
                response = self.request_reset(email=f'missing-{index}@example.com')
                self.assertEqual(response.status_code, 200)
            response = self.request_reset(email='missing-next@example.com')

        self.assertEqual(response.status_code, 429)
        self.assertFalse(SystemLog.objects.exists())
        warning.assert_called_once()
        self.assertNotIn('missing-1@example.com', ' '.join(map(str, warning.call_args.args)))


@override_settings(CACHES=THROTTLE_TEST_CACHE)
class ThrottleLogIsolationTests(ThrottleTestMixin, TestCase):
    def test_password_reset_throttle_log_remains_organization_scoped(self):
        first = Organization.objects.create(
            organization_name='First School', organization_code='FIRST',
        )
        second = Organization.objects.create(
            organization_name='Second School', organization_code='SECOND',
        )
        teacher = User.objects.create_user(
            username='first.teacher',
            email='first.teacher@example.com',
            password='FirstTeacher!2026',
            role=User.Role.TEACHER,
            organization=first,
        )
        first_admin = User.objects.create_user(
            username='first.admin',
            password='FirstAdmin!2026',
            role=User.Role.ORG_ADMIN,
            organization=first,
        )
        second_admin = User.objects.create_user(
            username='second.admin',
            password='SecondAdmin!2026',
            role=User.Role.ORG_ADMIN,
            organization=second,
        )
        reset_url = reverse('password-reset-request')
        for _ in range(settings.PASSWORD_RESET_THROTTLE_MAX_REQUESTS):
            self.client.post(
                reset_url,
                {'email': teacher.email},
                content_type='application/json',
                REMOTE_ADDR='203.0.113.30',
            )

        self.client.force_login(first_admin)
        first_logs = self.client.get(reverse('system-log-list')).json()['results']
        self.client.force_login(second_admin)
        second_logs = self.client.get(reverse('system-log-list')).json()['results']

        self.assertTrue(any('temporarily restricted' in item['activity'] for item in first_logs))
        self.assertFalse(any('temporarily restricted' in item['activity'] for item in second_logs))


class RequestIpTrustTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_forwarded_address_is_ignored_without_a_trusted_proxy(self):
        request = self.factory.get(
            '/',
            REMOTE_ADDR='192.0.2.10',
            HTTP_X_FORWARDED_FOR='198.51.100.99',
        )

        self.assertEqual(request_ip(request), '192.0.2.10')

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_client_address_is_selected_from_the_configured_proxy_chain(self):
        request = self.factory.get(
            '/',
            REMOTE_ADDR='192.0.2.10',
            HTTP_X_FORWARDED_FOR='198.51.100.99, 192.0.2.20',
        )

        self.assertEqual(request_ip(request), '198.51.100.99')
