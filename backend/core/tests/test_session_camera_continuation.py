from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Camera, CameraWorkerStatus, ClassroomSession, EngagementSummary
from .test_lesson_continuation import LessonFixtures


class SessionCameraContinuationTests(LessonFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.cameras = [
            Camera.objects.create(
                classroom=self.classroom, camera_name=position, position=position,
                ip_address=f'192.0.2.{index}',
            )
            for index, position in enumerate(('front', 'left', 'right'), start=1)
        ]
        self.headers = {'HTTP_X_PIPELINE_KEY': 'lesson-key'}

    def work(self):
        response = self.client.get(reverse('pipeline-work'), **self.headers)
        self.assertEqual(response.status_code, 200)
        return response.json()['sessions']

    def heartbeat(self, session, camera, state):
        response = self.client.post(reverse('pipeline-camera-heartbeat'), {
            'session_id': session.pk, 'camera_id': camera.pk, 'state': state,
            'source_type': 'simulated', 'pipeline_version': 'c3-test',
            'reason': {'online': 'processing', 'offline': 'retry_exhausted', 'stopped': 'shutdown'}.get(state, ''),
            'analysis_rate': 0, 'yolo_candidates': 0, 'valid_faces': 0,
            'confirmed_students': 0, 'unclassified_students': 0,
            'counts': {'engaged': 0, 'attentive': 0, 'confused': 0, 'bored': 0, 'disengaged': 0},
        }, content_type='application/json', **self.headers)
        return response

    def ready(self, session):
        for camera in self.cameras:
            self.assertIn(self.heartbeat(session, camera, 'starting').status_code, (200, 201))
            self.assertEqual(self.heartbeat(session, camera, 'online').status_code, 200)

    def first_meeting(self):
        response = self.post('session-prepare', {
            'subject': self.subject.pk, 'presentation': self.presentation.pk,
            'cameras': [camera.pk for camera in self.cameras],
        })
        self.assertEqual(response.status_code, 201)
        session = ClassroomSession.objects.get(pk=response.json()['id'])
        self.assertFalse(self.work()[0]['active'])
        self.assertIsNone(self.work()[0]['slide_event_id'])
        self.ready(session)
        self.assertEqual(self.post('session-start', pk=session.pk).status_code, 200)
        session.refresh_from_db()
        return session

    def payload(self, session, event_id):
        return {
            'schema_version': 2, 'ingestion_id': str(uuid4()),
            'pipeline_version': 'c3-test', 'session_id': session.pk,
            'slide_event_id': event_id, 'camera_id': self.cameras[0].pk,
            'captured_at': timezone.now().isoformat(),
            'counts': {'engaged': 1, 'attentive': 0, 'confused': 0, 'bored': 0, 'disengaged': 0},
            'total_detected': 1, 'unclassified_count': 0, 'average_confidence': 90,
        }

    def submit(self, payload):
        return self.client.post(reverse('engagement-ingestion'), payload, content_type='application/json', **self.headers)

    def test_save_continue_and_finish_follow_real_work_discovery_and_isolate_events(self):
        first = self.first_meeting()
        original_event = first.slide_events.get()
        accepted = self.payload(first, original_event.pk)
        self.assertEqual(self.submit(accepted).status_code, 201)
        self.post('session-enter-slide', {'slide': self.slides[11].pk}, first.pk)
        self.assertEqual(self.end(first).status_code, 200)
        self.assertEqual(self.work(), [])
        self.assertEqual(self.heartbeat(first, self.cameras[0], 'online').status_code, 400)
        self.assertEqual(self.heartbeat(first, self.cameras[0], 'stopped').status_code, 200)

        other = self.post('session-prepare', {'subject': self.subject.pk, 'presentation': self.presentation.pk})
        self.assertEqual(other.status_code, 201)
        self.assertEqual(self.client.delete(reverse('session-preparation-cancel', args=[other.json()['id']])).status_code, 204)

        second = self.continue_lesson(first, self.continuation_data(first, cameras=[camera.pk for camera in self.cameras]))
        preparing = self.work()
        self.assertEqual(len(preparing), 1)
        self.assertEqual(preparing[0]['session_id'], second.pk)
        self.assertFalse(preparing[0]['active'])
        self.assertIsNone(preparing[0]['slide_event_id'])
        self.assertEqual(self.start_prepared(second).status_code, 400)
        self.assertEqual(self.submit(self.payload(second, original_event.pk)).status_code, 400)

        self.ready(second)
        self.assertEqual(self.start_prepared(second).status_code, 200)
        active = self.work()[0]
        self.assertTrue(active['active'])
        self.assertEqual(active['slide_id'], self.slides[11].pk)
        self.assertNotEqual(active['slide_event_id'], original_event.pk)
        self.assertEqual({camera['camera_id'] for camera in active['cameras']}, {camera.pk for camera in self.cameras})
        self.assertEqual(self.submit(self.payload(second, original_event.pk)).status_code, 400)
        self.assertEqual(self.submit(self.payload(first, active['slide_event_id'])).status_code, 400)
        self.assertEqual(self.submit(self.payload(first, original_event.pk)).status_code, 400)
        self.assertEqual(self.submit(accepted).status_code, 200)
        self.assertEqual(self.submit(self.payload(second, active['slide_event_id'])).status_code, 201)
        self.assertEqual(EngagementSummary.objects.filter(event__session=first).count(), 1)
        self.assertEqual(EngagementSummary.objects.filter(event__session=second).count(), 1)
        self.assertEqual(self.end(second, 'finish').status_code, 200)
        self.assertEqual(self.work(), [])

    def test_start_preserves_prepared_worker_status_and_connection_identity(self):
        prepared = self.post('session-prepare', {
            'subject': self.subject.pk, 'presentation': self.presentation.pk,
            'cameras': [camera.pk for camera in self.cameras],
        })
        session = ClassroomSession.objects.get(pk=prepared.json()['id'])
        self.ready(session)
        before = list(CameraWorkerStatus.objects.filter(session=session).order_by('pk').values('pk', 'state', 'last_heartbeat'))

        self.assertEqual(self.post('session-start', pk=session.pk).status_code, 200)

        after = list(CameraWorkerStatus.objects.filter(session=session).order_by('pk').values('pk', 'state', 'last_heartbeat'))
        self.assertEqual(after, before)
        work = self.work()[0]
        self.assertEqual(work['session_id'], session.pk)
        self.assertTrue(work['active'])
        self.assertTrue(all(camera['state'] == 'online' for camera in work['cameras']))

    def test_offline_or_stopped_controller_preserves_saved_slide_and_retry(self):
        first = self.first_meeting()
        self.post('session-enter-slide', {'slide': self.slides[11].pk}, first.pk)
        self.end(first)
        second = self.continue_lesson(first, self.continuation_data(first, cameras=[camera.pk for camera in self.cameras]))
        self.assertEqual(self.start_prepared(second).status_code, 400)
        for camera in self.cameras:
            self.heartbeat(second, camera, 'starting')
            self.heartbeat(second, camera, 'stopped')
        self.assertEqual(self.start_prepared(second).status_code, 400)
        for camera in self.cameras:
            self.heartbeat(second, camera, 'starting')
            self.heartbeat(second, camera, 'offline' if camera == self.cameras[1] else 'online')
        self.assertEqual(self.start_prepared(second).status_code, 400)
        second.refresh_from_db()
        self.assertIsNone(second.started_at)
        self.assertEqual(second.lesson.state, 'saved')
        self.assertEqual(second.lesson.last_slide_id, self.slides[11].pk)
        self.assertFalse(second.slide_events.exists())
        failed = self.cameras[1]
        self.heartbeat(second, failed, 'starting')
        self.heartbeat(second, failed, 'online')
        self.assertEqual(self.start_prepared(second).status_code, 200)

    def test_cancelled_continuation_closes_discovery_and_keeps_saved_lesson(self):
        first = self.first_meeting()
        self.end(first)
        second = self.continue_lesson(first, self.continuation_data(first, cameras=[camera.pk for camera in self.cameras]))
        self.ready(second)
        self.assertEqual(self.client.delete(reverse('session-preparation-cancel', args=[second.pk])).status_code, 204)
        self.assertEqual(self.work(), [])
        first.lesson.refresh_from_db()
        self.assertEqual(first.lesson.state, 'saved')
        self.assertFalse(CameraWorkerStatus.objects.filter(session_id=second.pk).exists())
