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
    Camera, CameraWorkerStatus, Classroom, ClassroomSession, EngagementAlert,
    EngagementSummary, Organization, Presentation, PresentationSlide, SessionCamera,
    SlideEvent, Subject, User,
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

    def test_pipeline_context_follows_slide_changes_and_session_end(self):
        context_url = reverse('pipeline-session-context', args=[self.session.pk])
        headers = {'HTTP_X_PIPELINE_KEY': 'pipeline-test-key'}

        first = self.client.get(context_url, **headers)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()['active'])
        self.assertEqual(first.json()['slide_event_id'], self.event.pk)

        second_event = SlideEvent.objects.create(
            session=self.session,
            slide=self.second_slide,
            entered_at=timezone.now(),
        )
        second = self.client.get(context_url, **headers)
        self.assertEqual(second.json()['slide_event_id'], second_event.pk)

        self.session.ended_at = timezone.now()
        self.session.save(update_fields=['ended_at'])
        completed = self.client.get(context_url, **headers)
        self.assertFalse(completed.json()['active'])

    def test_pipeline_context_requires_the_worker_credential(self):
        context_url = reverse('pipeline-session-context', args=[self.session.pk])
        self.assertEqual(self.client.get(context_url).status_code, 403)
        self.assertEqual(
            self.client.get(context_url, HTTP_X_PIPELINE_KEY='wrong').status_code,
            403,
        )

    def test_counts_must_match_total_and_schema_must_be_supported(self):
        mismatch = self.submit(self.payload(total_detected=99))
        unsupported = self.submit(self.payload(schema_version=3))
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(unsupported.status_code, 400)

    def test_schema_two_requires_an_assigned_front_camera(self):
        classroom = self.session.subject.classroom
        front = Camera.objects.create(
            classroom=classroom, camera_name='Front Camera', position=Camera.Position.FRONT,
        )
        left = Camera.objects.create(
            classroom=classroom, camera_name='Left Camera', position=Camera.Position.LEFT,
        )
        SessionCamera.objects.bulk_create([
            SessionCamera(session=self.session, camera=front),
            SessionCamera(session=self.session, camera=left),
        ])

        missing = self.submit(self.payload(schema_version=2))
        side = self.submit(self.payload(schema_version=2, camera_id=left.pk))
        accepted = self.submit(self.payload(schema_version=2, camera_id=front.pk))

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(side.status_code, 400)
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(EngagementSummary.objects.get().camera_id, front.pk)

    def test_legacy_payload_is_rejected_for_a_real_multi_camera_session(self):
        classroom = self.session.subject.classroom
        for position in (Camera.Position.FRONT, Camera.Position.LEFT):
            camera = Camera.objects.create(
                classroom=classroom,
                camera_name=f'{position.title()} Camera',
                position=position,
            )
            SessionCamera.objects.create(session=self.session, camera=camera)

        response = self.submit()

        self.assertEqual(response.status_code, 400)
        self.assertIn('attributed Front camera', str(response.json()))

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


@override_settings(PIPELINE_API_KEY='pipeline-test-key', PIPELINE_HEARTBEAT_TIMEOUT_SECONDS=10)
class CameraOrchestrationApiTests(TestCase):
    def setUp(self):
        _, self.teacher, self.session, self.event, self.second_slide = create_context('orchestration')
        classroom = self.session.subject.classroom
        self.front = Camera.objects.create(
            classroom=classroom, camera_name='Center', position=Camera.Position.FRONT,
        )
        self.left = Camera.objects.create(
            classroom=classroom, camera_name='Left', position=Camera.Position.LEFT,
        )
        self.right = Camera.objects.create(
            classroom=classroom, camera_name='Right', position=Camera.Position.RIGHT,
        )
        SessionCamera.objects.bulk_create([
            SessionCamera(session=self.session, camera=camera)
            for camera in (self.front, self.left, self.right)
        ])
        self.work_url = reverse('pipeline-work')
        self.heartbeat_url = reverse('pipeline-camera-heartbeat')
        self.headers = {'HTTP_X_PIPELINE_KEY': 'pipeline-test-key'}

    def heartbeat(self, camera=None, **overrides):
        camera = camera or self.front
        payload = {
            'session_id': self.session.pk,
            'camera_id': camera.pk,
            'state': CameraWorkerStatus.State.STARTING,
            'source_type': CameraWorkerStatus.SourceType.SIMULATED,
            'reason': '',
            'pipeline_version': 'test-controller-1',
            'analysis_rate': '0.00',
            'yolo_candidates': 0,
            'valid_faces': 0,
            'confirmed_students': 0,
            'unclassified_students': 0,
            'counts': {
                'engaged': 0, 'attentive': 0, 'confused': 0,
                'bored': 0, 'disengaged': 0,
            },
        }
        payload.update(overrides)
        return self.client.post(
            self.heartbeat_url, payload, content_type='application/json', **self.headers,
        )

    def test_work_discovery_requires_key_and_returns_active_session_without_sources(self):
        self.assertEqual(self.client.get(self.work_url).status_code, 403)

        response = self.client.get(self.work_url, **self.headers)

        self.assertEqual(response.status_code, 200)
        work = response.json()['sessions'][0]
        self.assertEqual(work['session_id'], self.session.pk)
        self.assertEqual(work['slide_event_id'], self.event.pk)
        self.assertEqual([item['position'] for item in work['cameras']], ['front', 'left', 'right'])
        self.assertNotIn('source_path', str(response.json()).lower())
        self.assertNotIn('source_url', str(response.json()).lower())
        self.assertTrue(work['cameras'][0]['official_analytics'])
        self.assertFalse(work['cameras'][1]['official_analytics'])

    def test_work_discovery_tracks_slide_and_excludes_ended_sessions(self):
        new_event = SlideEvent.objects.create(
            session=self.session, slide=self.second_slide, entered_at=timezone.now(),
        )
        active = self.client.get(self.work_url, **self.headers).json()['sessions'][0]
        self.assertEqual(active['slide_event_id'], new_event.pk)

        self.session.ended_at = timezone.now()
        self.session.save(update_fields=['ended_at'])
        self.assertEqual(self.client.get(self.work_url, **self.headers).json()['sessions'], [])

    def test_heartbeat_enforces_assignment_metrics_and_state_transitions(self):
        online_first = self.heartbeat(state=CameraWorkerStatus.State.ONLINE)
        invalid_metrics = self.heartbeat(yolo_candidates=1, valid_faces=2)
        self.assertEqual(online_first.status_code, 400)
        self.assertEqual(invalid_metrics.status_code, 400)

        starting = self.heartbeat()
        online = self.heartbeat(
            state=CameraWorkerStatus.State.ONLINE,
            reason=CameraWorkerStatus.Reason.PROCESSING,
        )
        stopped = self.heartbeat(state=CameraWorkerStatus.State.STOPPED)
        invalid_restart = self.heartbeat(state=CameraWorkerStatus.State.ONLINE)

        self.assertEqual(starting.status_code, 201)
        self.assertEqual(online.status_code, 200)
        self.assertEqual(stopped.status_code, 200)
        self.assertEqual(invalid_restart.status_code, 400)

    def test_heartbeat_rejects_unassigned_camera_and_non_stopped_ended_session(self):
        other_classroom = Classroom.objects.create(
            organization=self.session.subject.classroom.organization,
            room_code='OTHER-101',
        )
        unassigned = Camera.objects.create(
            classroom=other_classroom, camera_name='Unassigned', position=Camera.Position.FRONT,
        )
        self.assertEqual(self.heartbeat(camera=unassigned).status_code, 404)

        self.session.ended_at = timezone.now()
        self.session.save(update_fields=['ended_at'])
        self.assertEqual(self.heartbeat().status_code, 400)
        self.assertEqual(
            self.heartbeat(state=CameraWorkerStatus.State.STOPPED).status_code,
            201,
        )

    def test_user_health_is_permission_scoped_and_marks_stale_workers_offline(self):
        self.assertEqual(self.heartbeat().status_code, 201)
        CameraWorkerStatus.objects.filter(
            session=self.session, camera=self.front,
        ).update(last_heartbeat=timezone.now() - timedelta(seconds=11))
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-camera-health', args=[self.session.pk]))

        self.assertEqual(response.status_code, 200)
        front = next(item for item in response.json()['cameras'] if item['camera_id'] == self.front.pk)
        self.assertEqual(front['state'], CameraWorkerStatus.State.OFFLINE)
        self.assertEqual(front['reason'], CameraWorkerStatus.Reason.HEARTBEAT_STALE)

        _, outsider, _, _, _ = create_context('health-outsider')
        self.client.force_login(outsider)
        self.assertEqual(
            self.client.get(reverse('session-camera-health', args=[self.session.pk])).status_code,
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
