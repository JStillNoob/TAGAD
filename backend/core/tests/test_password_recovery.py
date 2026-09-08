from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from ..models import SystemLog, User


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='http://localhost:5173',
)
class PasswordRecoveryTests(TestCase):
    password = 'Original-strong-password-2026!'

    def setUp(self):
        self.user = User.objects.create_user(
            username='recovery.teacher',
            email='recovery@example.com',
            password=self.password,
            role=User.Role.TEACHER,
        )
        self.request_url = reverse('password-reset-request')
        self.validate_url = reverse('password-reset-validate')
        self.confirm_url = reverse('password-reset-confirm')

    def token_data(self, user=None):
        user = user or self.user
        return {
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        }

    def test_request_has_same_response_for_known_and_unknown_email(self):
        known = self.client.post(self.request_url, {'email': 'RECOVERY@example.com'})
        unknown = self.client.post(self.request_url, {'email': 'missing@example.com'})

        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertNotIn('recovery@example.com', str(known.json()).lower())
        self.assertEqual(len(mail.outbox), 1)

    def test_request_sends_frontend_reset_link_and_records_activity(self):
        response = self.client.post(self.request_url, {'email': self.user.email})

        self.assertEqual(response.status_code, 200)
        self.assertIn('http://localhost:5173/reset-password/', mail.outbox[0].body)
        self.assertIn(self.user.username, mail.outbox[0].body)
        self.assertTrue(SystemLog.objects.filter(
            user=self.user,
            activity='Requested a password reset.',
        ).exists())

    def test_inactive_or_invalid_email_does_not_send_email(self):
        self.user.status = User.Status.INACTIVE
        self.user.save(update_fields=['status'])

        inactive = self.client.post(self.request_url, {'email': self.user.email})
        invalid = self.client.post(self.request_url, {'email': 'not-an-email'})

        self.assertEqual(inactive.status_code, 200)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_token_validation_accepts_valid_and_rejects_invalid_or_expired(self):
        data = self.token_data()
        valid = self.client.post(self.validate_url, data)
        invalid = self.client.post(self.validate_url, {**data, 'token': 'invalid-token'})
        with override_settings(PASSWORD_RESET_TIMEOUT=1):
            with patch.object(
                default_token_generator,
                '_now',
                return_value=datetime.now() - timedelta(seconds=2),
            ):
                expired_data = self.token_data()
            expired = self.client.post(self.validate_url, expired_data)

        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json(), {'valid': True})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(expired.status_code, 400)
        self.assertEqual(invalid.json(), expired.json())

    def test_confirm_applies_password_policy_and_matching_check(self):
        data = self.token_data()

        mismatch = self.client.post(self.confirm_url, {
            **data,
            'new_password': 'New-valid-password-2026!',
            'password_confirmation': 'Different-valid-password-2026!',
        })
        weak = self.client.post(self.confirm_url, {
            **data,
            'new_password': 'lowercase-password',
            'password_confirmation': 'lowercase-password',
        })

        self.assertEqual(mismatch.status_code, 400)
        self.assertIn('password_confirmation', mismatch.json())
        self.assertEqual(weak.status_code, 400)
        self.assertIn('new_password', weak.json())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    def test_confirm_changes_password_invalidates_token_and_records_activity(self):
        data = self.token_data()
        new_password = 'New-valid-password-2026!'

        changed = self.client.post(self.confirm_url, {
            **data,
            'new_password': new_password,
            'password_confirmation': new_password,
        })
        reused = self.client.post(self.confirm_url, {
            **data,
            'new_password': 'Another-valid-password-2026!',
            'password_confirmation': 'Another-valid-password-2026!',
        })

        self.assertEqual(changed.status_code, 204)
        self.assertEqual(reused.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertTrue(SystemLog.objects.filter(
            user=self.user,
            activity='Completed a password reset.',
        ).exists())

    def test_endpoints_are_available_without_authentication(self):
        data = self.token_data()

        requested = self.client.post(self.request_url, {'email': self.user.email})
        validated = self.client.post(self.validate_url, data)

        self.assertEqual(requested.status_code, 200)
        self.assertEqual(validated.status_code, 200)
