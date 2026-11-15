import tempfile
import threading
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.core.files.base import ContentFile
from django.apps import apps
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from ..analytics import build_session_analytics
from ..models import (
    Camera, CameraWorkerStatus, Classroom, ClassroomSession, LessonProgress,
    Organization, Presentation, PresentationSlide, Subject, User,
)
from ..presentation_processing import PresentationProcessingError, delete_presentation_files, process_presentation
from ..session_preparation import expire_prepared_sessions


class LessonFixtures:
    def setUp(self):
        super().setUp()
        media = tempfile.TemporaryDirectory()
        settings = override_settings(MEDIA_ROOT=media.name, PIPELINE_API_KEY='lesson-key')
        settings.enable()
        self.addCleanup(media.cleanup)
        self.addCleanup(settings.disable)
        self.organization = Organization.objects.create(organization_name='Lessons', organization_code='LESSONS')
        self.teacher = User.objects.create_user(username='lesson.teacher', organization=self.organization, role=User.Role.TEACHER)
        self.peer = User.objects.create_user(username='lesson.peer', organization=self.organization, role=User.Role.TEACHER)
        self.admin = User.objects.create_user(username='lesson.admin', organization=self.organization, role=User.Role.ORG_ADMIN)
        self.classroom = Classroom.objects.create(organization=self.organization, room_code='LESSON-ROOM')
        self.subject = Subject.objects.create(classroom=self.classroom, teacher=self.teacher, subject_code='LESSON-SUBJECT', subject_name='Long Presentation')
        self.presentation = Presentation.objects.create(
            user=self.teacher, title='25-slide lesson', file_name='lesson.pdf',
            processing_status=Presentation.ProcessingStatus.READY, total_slides=25,
        )
        self.presentation.file_path.save('lesson.pdf', ContentFile(b'%PDF-lesson-fixture'))
        first = PresentationSlide.objects.create(presentation=self.presentation, slide_number=1)
        first.image_path.save('slide.png', ContentFile(b'placeholder-image'))
        PresentationSlide.objects.bulk_create([
            PresentationSlide(presentation=self.presentation, slide_number=number, image_path=first.image_path.name)
            for number in range(2, 26)
        ])
        self.slides = list(self.presentation.slides.order_by('slide_number'))
        self.client.force_login(self.teacher)

    def post(self, name, data=None, pk=None, client=None):
        return (client or self.client).post(reverse(name, args=[pk] if pk else []), data or {}, content_type='application/json')

    def start(self):
        response = self.post('session-list', {'subject': self.subject.pk, 'presentation': self.presentation.pk, 'cameras': []})
        self.assertEqual(response.status_code, 201, response.content)
        return ClassroomSession.objects.get(pk=response.json()['id'])

    def end(self, session, action='save', client=None):
        session.refresh_from_db()
        session.lesson.refresh_from_db()
        return self.post('session-end', {'action': action, 'expected_revision': session.lesson.revision}, session.pk, client)

    def continuation_data(self, session, **overrides):
        session.refresh_from_db()
        session.lesson.refresh_from_db()
        data = {'request_id': str(uuid4()), 'expected_revision': session.lesson.revision, 'from_session': session.pk, 'cameras': []}
        data.update(overrides)
        return data

    def continue_lesson(self, session, data=None):
        response = self.post('lesson-continue', data or self.continuation_data(session), session.lesson_id)
        self.assertEqual(response.status_code, 201, response.content)
        return ClassroomSession.objects.get(pk=response.json()['id'])

    def start_prepared(self, session):
        session.lesson.refresh_from_db()
        return self.post('session-start', {'expected_revision': session.lesson.revision}, session.pk)


class LessonContinuationTests(LessonFixtures, TestCase):
    def test_owner_filter_restores_admins_own_class_on_a_paginated_list(self):
        self.client.force_login(self.admin)
        own = self.start()
        self.client.force_login(self.teacher)
        self.start()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('session-list'), {'status': 'ongoing', 'owner': 'me', 'page_size': 1}).json()
        self.assertEqual(response['count'], 1)
        self.assertEqual(response['results'][0]['id'], own.pk)

    def test_both_start_paths_create_lesson_once_and_preserve_legacy_end(self):
        direct = self.start()
        self.assertEqual(direct.lesson.last_slide_id, self.slides[0].pk)
        self.assertEqual(direct.lesson.organization_id, self.organization.pk)
        self.assertEqual(self.post('session-end', pk=direct.pk).status_code, 200)
        direct.lesson.refresh_from_db()
        self.assertEqual(direct.lesson.state, 'completed')
        prepared = self.post('session-prepare', {'subject': self.subject.pk, 'presentation': self.presentation.pk})
        self.assertEqual(prepared.status_code, 201)
        self.assertIsNone(prepared.json()['lesson'])
        self.assertEqual(self.post('session-start', pk=prepared.json()['id']).status_code, 200)
        repeated = self.post('session-start', pk=prepared.json()['id'])
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(LessonProgress.objects.count(), 2)
        self.assertEqual(ClassroomSession.objects.get(pk=prepared.json()['id']).slide_events.count(), 1)

    def test_multiday_lesson_restores_slide_and_keeps_meeting_durations(self):
        start = timezone.now().replace(hour=1, minute=0, second=0, microsecond=0)
        with patch('core.session_lifecycle.timezone.now', return_value=start):
            first = self.start()
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(minutes=10)):
            moved = self.post('session-enter-slide', {'slide': self.slides[11].pk, 'expected_revision': 1}, first.pk)
        self.assertEqual(moved.status_code, 201)
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(minutes=40)):
            self.assertEqual(self.end(first).status_code, 200)
        other = self.start()
        self.assertEqual(self.end(other, 'finish').status_code, 200)
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(days=1, minutes=-5)):
            second = self.continue_lesson(first)
        ClassroomSession.objects.filter(pk=second.pk).update(prepared_at=start + timedelta(days=1, minutes=-5))
        self.assertEqual(second.lesson.last_slide_id, self.slides[11].pk)
        detail = self.client.get(reverse('session-detail', args=[second.pk])).json()
        self.assertEqual(detail['current_slide'], self.slides[11].pk)
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(days=1)):
            started = self.start_prepared(second)
        self.assertEqual(started.status_code, 200, started.content)
        self.assertEqual(started.json()['current_slide'], self.slides[11].pk)
        with patch('core.session_lifecycle.timezone.now', return_value=start + timedelta(days=1, minutes=40)):
            self.assertEqual(self.end(second, 'finish').status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.lesson_id, second.lesson_id)
        self.assertEqual(second.continued_from_id, first.pk)
        for meeting in (first, second):
            analytics = build_session_analytics(meeting)
            self.assertEqual(analytics['session']['duration_seconds'], 2400)
            self.assertEqual(sum(slide['duration_seconds'] for slide in analytics['slides']), 2400)
        history = self.client.get(reverse('session-list'), {'lesson': first.lesson_id}).json()
        self.assertEqual(history['count'], 2)

    def test_save_requires_current_revision_and_atomic_slide_progress(self):
        session = self.start()
        self.assertEqual(self.post('session-end', {'action': 'save'}, session.pk).status_code, 400)
        for invalid in (True, '1', 1.0, 0):
            self.assertEqual(self.post('session-end', {'action': 'save', 'expected_revision': invalid}, session.pk).status_code, 400)
        self.assertEqual(self.post('session-enter-slide', {'slide': self.slides[11].pk, 'expected_revision': 1}, session.pk).status_code, 201)
        stale = self.post('session-end', {'action': 'save', 'expected_revision': 1}, session.pk)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['lesson_revision'], 2)
        session.refresh_from_db()
        self.assertIsNone(session.ended_at)
        self.assertEqual(self.end(session).status_code, 200)
        session.lesson.refresh_from_db()
        self.assertEqual(session.lesson.last_slide_id, self.slides[11].pk)

    def test_repeated_save_and_conflicting_finish_do_not_touch_later_meeting(self):
        first = self.start()
        saved = self.end(first)
        second = self.continue_lesson(first)
        self.assertEqual(self.start_prepared(second).status_code, 200)
        repeated = self.post('session-end', {'action': 'save', 'expected_revision': 1}, first.pk)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()['ended_at'], saved.json()['ended_at'])
        self.assertEqual(repeated.json()['end_action'], 'save')
        self.assertEqual(self.post('session-end', {'action': 'finish'}, first.pk).status_code, 409)
        second.refresh_from_db()
        self.assertIsNone(second.ended_at)
        self.assertEqual(second.lesson.state, 'active')

    def test_continuation_key_replays_same_meeting_and_rejects_changed_input(self):
        first = self.start()
        self.end(first)
        data = self.continuation_data(first)
        second = self.continue_lesson(first, data)
        repeated = self.post('lesson-continue', data, first.lesson_id)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()['id'], second.pk)
        self.assertEqual(repeated.json()['continuation_request_id'], data['request_id'])
        self.assertEqual(self.post('lesson-continue', dict(data, cameras=[999]), first.lesson_id).status_code, 409)
        self.assertEqual(self.post('lesson-continue', dict(data, request_id=str(uuid4())), first.lesson_id).status_code, 409)
        self.assertEqual(self.start_prepared(second).status_code, 200)
        self.end(second, 'finish')
        self.assertEqual(self.post('lesson-continue', data, first.lesson_id).json()['id'], second.pk)

    def test_cancellation_preserves_progress_and_rejects_old_preparation_retry(self):
        first = self.start()
        self.end(first)
        data = self.continuation_data(first)
        second = self.continue_lesson(first, data)
        self.assertEqual(self.client.delete(reverse('session-preparation-cancel', args=[second.pk])).status_code, 204)
        self.assertFalse(ClassroomSession.objects.filter(pk=second.pk).exists())
        self.assertEqual(self.post('lesson-continue', data, first.lesson_id).status_code, 409)
        lesson = self.client.get(reverse('lesson-detail', args=[first.lesson_id])).json()
        self.assertEqual(lesson['state'], 'saved')
        self.assertTrue(lesson['can_continue'])
        self.continue_lesson(first)

    def test_expiry_preserves_lesson_and_releases_reservation(self):
        first = self.start()
        self.end(first)
        second = self.continue_lesson(first)
        ClassroomSession.objects.filter(pk=second.pk).update(prepared_at=timezone.now() - timedelta(minutes=31))
        self.assertGreater(expire_prepared_sessions(user=self.teacher), 0)
        self.assertFalse(ClassroomSession.objects.filter(pk=second.pk).exists())
        first.lesson.refresh_from_db()
        self.assertEqual(first.lesson.state, 'saved')
        self.continue_lesson(first)

    def test_expiry_rechecks_started_state_after_acquiring_lock(self):
        first = self.start()
        self.end(first)
        second = self.continue_lesson(first)
        ClassroomSession.objects.filter(pk=second.pk).update(prepared_at=timezone.now() - timedelta(minutes=31))

        @contextmanager
        def started_before_cleanup_locked(session_id):
            # The candidate query saw a draft, but Start committed before its lock.
            with transaction.atomic():
                second.lesson.refresh_from_db()
                from ..session_lifecycle import start_meeting
                start_meeting(second, revision=second.lesson.revision)
                yield second

        with patch('core.session_preparation.locked_meeting', side_effect=started_before_cleanup_locked):
            self.assertEqual(expire_prepared_sessions(user=self.teacher), 0)
        second.refresh_from_db()
        self.assertIsNotNone(second.started_at)
        self.assertIsNone(second.ended_at)

    def test_backward_migration_refuses_to_discard_persisted_progress(self):
        migration = import_module('core.migrations.0017_session_continuation')
        editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        migration.protect_lesson_progress(apps, editor)
        self.start()
        with self.assertRaisesRegex(RuntimeError, 'persisted lesson progress'):
            migration.protect_lesson_progress(apps, editor)

    def test_revisited_and_final_slides_remain_explicitly_resumable(self):
        for number in (12, 2):
            if number == 12:
                first = self.start()
            self.assertEqual(self.post('session-enter-slide', {'slide': self.slides[number - 1].pk}, first.pk).status_code, 201)
        self.end(first)
        second = self.continue_lesson(first)
        self.assertEqual(self.start_prepared(second).json()['current_slide'], self.slides[1].pk)
        self.post('session-enter-slide', {'slide': self.slides[24].pk}, second.pk)
        self.end(second)
        third = self.continue_lesson(second)
        self.assertEqual(self.start_prepared(third).json()['current_slide'], self.slides[24].pk)

    def test_unavailable_media_keeps_progress_and_saved_finish_needs_no_cameras(self):
        first = self.start()
        self.end(first)
        first.lesson.last_slide.image_path.delete(save=False)
        failed = self.post('lesson-continue', self.continuation_data(first), first.lesson_id)
        self.assertEqual(failed.status_code, 400)
        first.lesson.refresh_from_db()
        self.assertEqual(first.lesson.state, 'saved')
        finished = self.post('lesson-finish', {'expected_revision': first.lesson.revision}, first.lesson_id)
        self.assertEqual(finished.status_code, 200)
        self.assertEqual(finished.json()['state'], 'completed')
        self.assertEqual(self.post('lesson-finish', {'expected_revision': 1}, first.lesson_id).status_code, 200)
        self.assertEqual(ClassroomSession.objects.count(), 1)

    def test_reassignment_blocks_continue_but_owner_can_finish_saved_lesson(self):
        first = self.start()
        self.end(first)
        self.subject.teacher = self.peer
        self.subject.save(update_fields=['teacher'])
        self.assertEqual(self.post('lesson-continue', self.continuation_data(first), first.lesson_id).status_code, 400)
        first.lesson.refresh_from_db()
        self.assertEqual(self.post('lesson-finish', {'expected_revision': first.lesson.revision}, first.lesson_id).status_code, 200)

    def test_storage_failure_is_actionable_and_keeps_saved_progress(self):
        first = self.start()
        self.end(first)
        with patch.object(self.presentation.file_path.storage, 'exists', side_effect=OSError('unavailable')):
            detail = self.client.get(reverse('lesson-detail', args=[first.lesson_id])).json()
            self.assertFalse(detail['can_continue'])
            self.assertIn('storage is unavailable', detail['blocking_reason'])
            response = self.post('lesson-continue', self.continuation_data(first), first.lesson_id)
        self.assertEqual(response.status_code, 400)
        first.lesson.refresh_from_db()
        self.assertEqual(first.lesson.state, 'saved')

    def test_saved_and_prepared_lesson_reads_are_paginated_and_searchable(self):
        first = self.start()
        self.end(first)
        page = self.client.get(reverse('lesson-list'), {'status': 'saved', 'search': '25-slide', 'page_size': 1}).json()
        self.assertEqual(page['count'], 1)
        self.assertEqual(page['results'][0]['latest_session'], first.pk)
        second = self.continue_lesson(first)
        detail = self.client.get(reverse('lesson-detail', args=[first.lesson_id])).json()
        self.assertEqual(detail['display_state'], 'Preparing to Continue')
        self.assertEqual(detail['prepared_session'], second.pk)
        self.assertFalse(detail['can_continue'])
        self.assertEqual(self.post('lesson-finish', {'expected_revision': detail['revision']}, first.lesson_id).status_code, 409)
        self.assertEqual(self.client.get(reverse('lesson-list'), {'status': 'unknown'}).status_code, 400)

    def test_teacher_ownership_and_organization_isolation_cover_direct_routes(self):
        first = self.start()
        self.end(first)
        payload = self.continuation_data(first)
        foreign_org = Organization.objects.create(organization_name='Foreign', organization_code='FOREIGN')
        foreign = User.objects.create_user(username='foreign.teacher', organization=foreign_org, role=User.Role.TEACHER)
        for actor in (self.peer, self.admin, foreign):
            self.client.force_login(actor)
            self.assertEqual(self.client.get(reverse('lesson-detail', args=[first.lesson_id])).status_code, 404)
            self.assertEqual(self.post('lesson-continue', payload, first.lesson_id).status_code, 404)
            self.assertEqual(self.post('lesson-finish', {'expected_revision': 2}, first.lesson_id).status_code, 404)
            self.assertEqual(self.post('session-end', {'action': 'save'}, first.pk).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('session-detail', args=[first.pk])).status_code, 200)
        self.teacher.organization = foreign_org
        self.teacher.save(update_fields=['organization'])
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse('session-detail', args=[first.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('lesson-list')).json()['count'], 0)

    def test_continuation_requires_fresh_selected_camera_heartbeat(self):
        first = self.start()
        self.end(first)
        camera = Camera.objects.create(classroom=self.classroom, camera_name='Front', position='front')
        second = self.continue_lesson(first, self.continuation_data(first, cameras=[camera.pk]))
        self.assertEqual(self.start_prepared(second).status_code, 400)
        self.assertEqual(second.slide_events.count(), 0)
        CameraWorkerStatus.objects.create(
            session=second, camera=camera, state='online', source_type='simulated',
            pipeline_version='test', latest_counts={},
        )
        self.assertEqual(self.start_prepared(second).status_code, 200)

    def test_saved_dependencies_protect_files_and_archiving(self):
        first = self.start()
        self.end(first)
        self.assertEqual(self.client.delete(reverse('presentation-detail', args=[self.presentation.pk])).status_code, 400)
        self.assertEqual(self.client.delete(reverse('session-lifecycle', args=[first.pk])).status_code, 400)
        for operation in (delete_presentation_files, process_presentation):
            with self.assertRaises(PresentationProcessingError):
                operation(self.presentation)
        self.assertTrue(self.presentation.file_path.storage.exists(self.presentation.file_path.name))
        self.assertTrue(self.slides[0].image_path.storage.exists(self.slides[0].image_path.name))
        first.lesson.refresh_from_db()
        self.post('lesson-finish', {'expected_revision': first.lesson.revision}, first.lesson_id)
        self.assertEqual(self.client.delete(reverse('presentation-detail', args=[self.presentation.pk])).status_code, 204)

    def test_legacy_meeting_keeps_null_lesson_and_finish_behavior(self):
        legacy = ClassroomSession.objects.create(
            user=self.teacher, subject=self.subject, presentation=self.presentation,
            session_date=timezone.localdate(), started_at=timezone.now(),
        )
        self.assertEqual(self.post('session-end', {'action': 'save', 'expected_revision': 1}, legacy.pk).status_code, 400)
        finished = self.post('session-end', pk=legacy.pk)
        self.assertEqual(finished.status_code, 200)
        self.assertIsNone(finished.json()['lesson'])
        self.assertEqual(finished.json()['end_action'], '')
        self.assertFalse(LessonProgress.objects.exists())

    def test_database_rejects_invalid_outcomes_revisions_and_multiple_successors(self):
        first = self.start()
        with self.assertRaises(IntegrityError), transaction.atomic():
            LessonProgress.objects.filter(pk=first.lesson_id).update(revision=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ClassroomSession.objects.filter(pk=first.pk).update(end_action='save')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ClassroomSession.objects.filter(pk=first.pk).update(ended_at=timezone.now())
        self.end(first)
        second = self.continue_lesson(first)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ClassroomSession.objects.create(
                user=self.peer, subject=self.subject, presentation=self.presentation,
                lesson=first.lesson, continued_from=first, continuation_request_id=uuid4(),
                session_date=timezone.localdate(),
            )
        self.assertTrue(ClassroomSession.objects.filter(pk=second.pk).exists())


@skipUnlessDBFeature('has_select_for_update')
class LessonConcurrencyTests(LessonFixtures, TransactionTestCase):
    def race(self, *actions):
        barrier = threading.Barrier(len(actions))

        def perform(action):
            close_old_connections()
            try:
                client = Client()
                client.force_login(User.objects.get(pk=self.teacher.pk))
                barrier.wait(timeout=10)
                return action(client)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(perform, actions))

    def test_same_continuation_key_creates_one_preparation(self):
        first = self.start()
        self.end(first)
        data = self.continuation_data(first)
        responses = self.race(*[
            lambda client: self.post('lesson-continue', data, first.lesson_id, client)
            for _index in range(2)
        ])
        self.assertEqual(sorted(response.status_code for response in responses), [200, 201])
        self.assertEqual(len({response.json()['id'] for response in responses}), 1)

    def test_different_keys_cannot_fork_a_saved_meeting(self):
        first = self.start()
        self.end(first)
        left, right = self.continuation_data(first), self.continuation_data(first)
        responses = self.race(
            lambda client: self.post('lesson-continue', left, first.lesson_id, client),
            lambda client: self.post('lesson-continue', right, first.lesson_id, client),
        )
        self.assertEqual(sorted(response.status_code for response in responses), [201, 409])
        self.assertEqual(first.continuations.count(), 1)

    def test_save_and_finish_commit_one_terminal_action(self):
        first = self.start()
        responses = self.race(
            lambda client: self.post('session-end', {'action': 'save', 'expected_revision': 1}, first.pk, client),
            lambda client: self.post('session-end', {'action': 'finish', 'expected_revision': 1}, first.pk, client),
        )
        self.assertEqual(sorted(response.status_code for response in responses), [200, 409])
        first.refresh_from_db()
        self.assertIn(first.end_action, ('save', 'finish'))
        self.assertEqual(first.lesson.state, 'saved' if first.end_action == 'save' else 'completed')

    def test_save_and_slide_navigation_preserve_acknowledged_progress(self):
        first = self.start()
        responses = self.race(
            lambda client: self.post('session-end', {'action': 'save', 'expected_revision': 1}, first.pk, client),
            lambda client: self.post('session-enter-slide', {'slide': self.slides[11].pk, 'expected_revision': 1}, first.pk, client),
        )
        self.assertIn(sorted(response.status_code for response in responses), ([200, 400], [201, 409]))
        first.refresh_from_db()
        self.assertEqual(first.lesson.last_slide_id, first.slide_events.order_by('-entered_at', '-pk').first().slide_id)

    def test_start_and_cancel_serialize_the_same_preparation(self):
        first = self.start()
        self.end(first)
        second = self.continue_lesson(first)
        second.lesson.refresh_from_db()
        responses = self.race(
            lambda client: self.post('session-start', {'expected_revision': second.lesson.revision}, second.pk, client),
            lambda client: client.delete(reverse('session-preparation-cancel', args=[second.pk])),
        )
        self.assertIn(sorted(response.status_code for response in responses), ([200, 400], [204, 404]))
        first.lesson.refresh_from_db()
        self.assertEqual(first.lesson.state, 'active' if responses[0].status_code == 200 else 'saved')
