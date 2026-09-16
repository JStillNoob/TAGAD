import json
import logging

from django.test import SimpleTestCase, override_settings
from django.urls import path
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.observability import SafeJsonFormatter


class FailingView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError('DB_PASSWORD=top-secret student=private-name')


class SensitiveServerError(APIException):
    status_code = 500
    default_detail = 'storage password=private-value'


class HandledFailingView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        raise SensitiveServerError()


urlpatterns = [
    path('api/failing/', FailingView.as_view()),
    path('api/handled-failing/', HandledFailingView.as_view()),
]


class StructuredLoggingTests(SimpleTestCase):
    def test_formatter_emits_json_and_redacts_sensitive_values(self):
        formatter = SafeJsonFormatter()
        record = logging.LogRecord(
            name='tagad.test',
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg='failed DB_PASSWORD=hunter2 reset_token=reset-secret authorization=Bearer-secret',
            args=(),
            exc_info=None,
        )
        record.request_id = 'request-123'

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload['request_id'], 'request-123')
        self.assertEqual(payload['level'], 'ERROR')
        self.assertNotIn('hunter2', payload['message'])
        self.assertNotIn('reset-secret', payload['message'])
        self.assertNotIn('Bearer-secret', payload['message'])
        self.assertIn('[REDACTED]', payload['message'])

    @override_settings(ROOT_URLCONF=__name__)
    def test_unexpected_api_error_is_generic_and_traceable(self):
        response = self.client.get(
            '/api/failing/',
            HTTP_X_REQUEST_ID='failure-reference-123',
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {
            'detail': 'Something went wrong. Please try again or contact an administrator.',
            'request_id': 'failure-reference-123',
        })
        self.assertEqual(response['X-Request-ID'], 'failure-reference-123')
        self.assertNotIn('top-secret', response.content.decode())
        self.assertNotIn('private-name', response.content.decode())

    @override_settings(ROOT_URLCONF=__name__)
    def test_handled_server_error_detail_is_also_replaced(self):
        response = self.client.get('/api/handled-failing/')

        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private-value', response.content.decode())
        self.assertIn(response['X-Request-ID'], response.content.decode())
