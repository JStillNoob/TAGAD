from unittest.mock import patch

from django.test import TestCase


class OperationalHealthTests(TestCase):
    def test_liveness_is_public_and_returns_request_id(self):
        response = self.client.get('/api/health/live/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response['X-Request-ID'], response.json()['request_id'])

    @patch('core.health.check_websocket', return_value=True)
    @patch('core.health.check_presentation_converter', return_value=True)
    @patch('core.health.check_storage', return_value=True)
    @patch('core.health.check_database', return_value=True)
    def test_readiness_reports_each_required_component(self, *_checks):
        response = self.client.get('/api/health/ready/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ready')
        self.assertEqual(response.json()['checks'], {
            'django': {'status': 'ok'},
            'postgresql': {'status': 'ok'},
            'file_storage': {'status': 'ok'},
            'presentation_converter': {'status': 'ok'},
            'websocket': {'status': 'ok'},
        })

    @patch('core.health.check_websocket', return_value=True)
    @patch('core.health.check_presentation_converter', return_value=True)
    @patch('core.health.check_storage', side_effect=RuntimeError('password=do-not-log'))
    @patch('core.health.check_database', return_value=True)
    def test_readiness_identifies_failure_without_exposing_exception(self, *_checks):
        response = self.client.get('/api/health/ready/')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['status'], 'unavailable')
        self.assertEqual(response.json()['checks']['file_storage'], {'status': 'failed'})
        self.assertNotIn('do-not-log', response.content.decode())

    def test_invalid_caller_request_id_is_replaced(self):
        response = self.client.get(
            '/api/health/live/',
            HTTP_X_REQUEST_ID='not valid / contains spaces',
        )

        self.assertNotEqual(response['X-Request-ID'], 'not valid / contains spaces')
        self.assertRegex(response['X-Request-ID'], r'^[a-f0-9-]{36}$')

    def test_safe_caller_request_id_is_preserved(self):
        response = self.client.get(
            '/api/health/live/',
            HTTP_X_REQUEST_ID='operator-check-123',
        )

        self.assertEqual(response['X-Request-ID'], 'operator-check-123')

