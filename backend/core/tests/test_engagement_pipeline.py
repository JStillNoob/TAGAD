from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Classroom, ClassroomSession, EngagementAlert, EngagementSummary,
    Organization, Presentation, PresentationSlide, SlideEvent, Subject, User,
)
from core.routing import websocket_urlpatterns
from core.engagement_pipeline import ingest_engagement


def create_context(prefix='pipeline'):
    organization = Organization.objects.create(
        organization_name=f'{prefix} School', organization_code=prefix.upper(),
    )
    teacher = User.objects.create_user(
        username=f'{prefix}.teacher', organization=organization, role=User.Role.TEACHER,
    )
    classroom = Classroom.objects.create(organization=organization, room_code=f'{prefix}-101')
    subject = Subject.objects.create(
        classroom=classroom, teacher=teacher,
        subject_code=f'{prefix}-IT', subject_name='Pipeline Testing',
    )
    presentation = Presentation.objects.create(
        user=teacher, title='Pipeline Slides', file_name='pipeline.pdf',
        processing_status=Presentation.ProcessingStatus.READY, total_slides=2,
    )
    first = PresentationSlide.objects.create(
        presentation=presentation, slide_number=1, slide_title='First',
    )
    second = PresentationSlide.objects.create(
        presentation=presentation, slide_number=2, slide_title='Second',
    )
    session = ClassroomSession.objects.create(
        user=teacher, subject=subject, presentation=presentation,
        session_date=timezone.localdate(), started_at=timezone.now(),
    )
    event = SlideEvent.objects.create(session=session, slide=first, entered_at=session.started_at)
    return organization, teacher, session, event, second


@override_settings(PIPELINE_API_KEY='pipeline-test-key', ENGAGEMENT_ALERT_CONSECUTIVE_WINDOWS=3)
class EngagementIngestionTests(TestCase):
    def setUp(self):
        _, self.teacher, self.session, self.event, self.second_slide = create_context()
        self.url = reverse('engagement-ingestion')

    def payload(self, **overrides):
        data = {
            'schema_version': 1,
            'ingestion_id': str(uuid4()),
            'pipeline_version': 'test-pipeline-1',
            'session_id': self.session.pk,
            'slide_event_id': self.event.pk,
            'captured_at': timezone.now().isoformat(),
            'counts': {'engaged': 18, 'attentive': 6, 'confused': 2, 'bored': 1, 'disengaged': 3},
            'total_detected': 32,
            'unclassified_count': 2,
            'average_confidence': '86.50',
        }
        data.update(overrides)
        return data

    def submit(self, payload=None, key='pipeline-test-key'):
        return self.client.post(
            self.url, payload or self.payload(), content_type='application/json',
            HTTP_X_PIPELINE_KEY=key,
        )

    def test_valid_payload_is_stored_and_serialized(self):
        response = self.submit()
        self.assertEqual(response.status_code, 201)
        summary = EngagementSummary.objects.get()
        self.assertEqual(summary.total_detected, 32)
        self.assertEqual(summary.unclassified_count, 2)
        self.assertEqual(summary.pipeline_version, 'test-pipeline-1')
        self.assertEqual(response.json()['distribution']['engaged'], 60.0)

    def test_key_and_configuration_are_required(self):
        self.assertEqual(self.submit(key='wrong').status_code, 403)
        with override_settings(PIPELINE_API_KEY=''):
            self.assertEqual(self.submit().status_code, 503)
        self.assertFalse(EngagementSummary.objects.exists())

    def test_counts_must_match_total_and_schema_must_be_supported(self):
        mismatch = self.submit(self.payload(total_detected=99))
        unsupported = self.submit(self.payload(schema_version=2))
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(unsupported.status_code, 400)

    def test_duplicate_ingestion_is_idempotent(self):
        payload = self.payload()
        self.assertEqual(self.submit(payload).status_code, 201)
        self.assertEqual(self.submit(payload).status_code, 200)
        self.assertEqual(EngagementSummary.objects.count(), 1)

    def test_rejects_completed_mismatched_and_stale_slide_events(self):
        other = SlideEvent.objects.create(
            session=self.session, slide=self.second_slide, entered_at=timezone.now() + timedelta(seconds=1),
        )
        self.assertEqual(self.submit().status_code, 400)
        self.session.ended_at = timezone.now()
        self.session.save(update_fields=['ended_at'])
        self.assertEqual(self.submit(self.payload(slide_event_id=other.pk)).status_code, 400)

    def test_alert_requires_three_windows_and_rearms_after_recovery(self):
        high = {'engaged': 2, 'attentive': 2, 'confused': 2, 'bored': 3, 'disengaged': 21}
        for _ in range(2):
            self.assertIsNone(self.submit(self.payload(counts=high)).json()['alert'])
        self.assertIsNotNone(self.submit(self.payload(counts=high)).json()['alert'])
        self.assertIsNone(self.submit(self.payload(counts=high)).json()['alert'])
        self.assertEqual(EngagementAlert.objects.count(), 1)

        self.submit(self.payload())
        for _ in range(3):
            last = self.submit(self.payload(counts=high)).json()
        self.assertIsNotNone(last['alert'])
        self.assertEqual(EngagementAlert.objects.count(), 2)

    @override_settings(DEBUG=True, ENABLE_PIPELINE_SIMULATOR=True)
    def test_simulator_is_owner_scoped_and_feeds_analytics(self):
        self.client.force_login(self.teacher)
        response = self.client.post(reverse('engagement-simulator', args=[self.session.pk]))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['pipeline_version'], 'simulator-1')
        analytics = self.client.get(reverse('session-analytics', args=[self.session.pk])).json()
        self.assertTrue(analytics['has_data'])

        _, other_teacher, _, _, _ = create_context('foreign')
        self.client.force_login(other_teacher)
        self.assertEqual(
            self.client.post(reverse('engagement-simulator', args=[self.session.pk])).status_code,
            404,
        )

    @override_settings(ENABLE_PIPELINE_SIMULATOR=False)
    def test_simulator_is_hidden_when_disabled(self):
        self.client.force_login(self.teacher)
        self.assertEqual(
            self.client.post(reverse('engagement-simulator', args=[self.session.pk])).status_code,
            404,
        )


class EngagementWebsocketPermissionTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        _, self.teacher, self.session, _, _ = create_context('socket')
        _, self.outsider, _, _, _ = create_context('outsider')

    async def test_socket_is_scoped_to_users_who_can_access_the_session(self):
        allowed = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f'/ws/sessions/{self.session.pk}/engagement/',
        )
        allowed.scope['user'] = self.teacher
        connected, _ = await allowed.connect()
        self.assertTrue(connected)
        await allowed.disconnect()

        denied = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns), f'/ws/sessions/{self.session.pk}/engagement/',
        )
        denied.scope['user'] = self.outsider
        connected, close_code = await denied.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    async def test_ingestion_is_broadcast_to_the_authorized_session_socket(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/sessions/{self.session.pk}/engagement/',
        )
        communicator.scope['user'] = self.teacher
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        event = await sync_to_async(self.session.slide_events.get)()
        await sync_to_async(ingest_engagement)({
            'schema_version': 1,
            'ingestion_id': uuid4(),
            'pipeline_version': 'socket-test-1',
            'session_id': self.session.pk,
            'slide_event_id': event.pk,
            'captured_at': timezone.now(),
            'counts': {'engaged': 18, 'attentive': 6, 'confused': 2, 'bored': 1, 'disengaged': 3},
            'total_detected': 32,
            'unclassified_count': 2,
            'average_confidence': Decimal('86.50'),
        })
        message = await communicator.receive_json_from(timeout=1)
        self.assertEqual(message['type'], 'engagement.summary')
        self.assertEqual(message['data']['pipeline_version'], 'socket-test-1')
        await communicator.disconnect()
