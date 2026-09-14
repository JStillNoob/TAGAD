import io
import subprocess
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pymupdf
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Camera,
    Classroom,
    ClassroomSession,
    Organization,
    Presentation,
    PresentationSlide,
    SessionCamera,
    SlideEvent,
    Subject,
    SystemLog,
    User,
)
from ..session_access import presentations_for_update


def make_pdf(page_count=2):
    document = pymupdf.open()
    for number in range(1, page_count + 1):
        page = document.new_page(width=640, height=360)
        page.insert_text((60, 80), f'Test slide {number}', fontsize=24)
    content = document.tobytes()
    document.close()
    return content


def make_pptx(expanded_payload=0):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('ppt/presentation.xml', '<p:presentation/>')
        if expanded_payload:
            archive.writestr('ppt/media/large.bin', b'x' * expanded_payload)
    return buffer.getvalue()


class PresentationAndSessionTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
            PRESENTATION_MAX_UPLOAD_BYTES=5 * 1024 * 1024,
            PRESENTATION_MAX_EXPANDED_BYTES=10 * 1024 * 1024,
            PRESENTATION_MAX_SLIDES=20,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.organization = Organization.objects.create(
            organization_name='Tagad University',
            organization_code='TAGAD-U',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other University',
            organization_code='OTHER-U',
        )
        self.system_admin = User.objects.create_superuser(
            username='system.admin',
            email='system@example.com',
            password='A-strong-test-password-2026',
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='org.admin',
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='teacher.other',
            organization=self.other_organization,
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-101',
        )
        self.other_classroom = Classroom.objects.create(
            organization=self.other_organization,
            room_code='ROOM-201',
        )
        self.subject = Subject.objects.create(
            classroom=self.classroom,
            teacher=self.teacher,
            subject_code='IT-301',
            subject_name='Data Structures',
        )
        self.other_subject = Subject.objects.create(
            classroom=self.other_classroom,
            teacher=self.other_teacher,
            subject_code='IT-401',
            subject_name='Networks',
        )
        self.front_camera = Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position=Camera.Position.FRONT,
        )
        self.left_camera = Camera.objects.create(
            classroom=self.classroom,
            camera_name='Left Camera',
            position=Camera.Position.LEFT,
            status=Camera.Status.INACTIVE,
        )

    def create_ready_presentation(self, user=None, title='Test Presentation', pages=2):
        presentation = Presentation.objects.create(
            user=user or self.teacher,
            title=title,
            file_name='lecture.pdf',
            file_type=Presentation.FileType.PDF,
            processing_status=Presentation.ProcessingStatus.READY,
            total_slides=pages,
        )
        presentation.file_path.save('lecture.pdf', ContentFile(make_pdf(pages)), save=True)
        for number in range(1, pages + 1):
            slide = PresentationSlide.objects.create(
                presentation=presentation,
                slide_number=number,
                slide_title=f'Slide {number}',
            )
            slide.image_path.save(
                f'slide-{number}.png',
                ContentFile(b'png image placeholder'),
                save=True,
            )
        return presentation

    def upload(self, name, content, content_type, title='Uploaded Lecture'):
        return self.client.post(
            reverse('presentation-list'),
            {
                'title': title,
                'file': SimpleUploadedFile(name, content, content_type=content_type),
            },
        )

    def test_presentation_row_lock_targets_only_the_presentation_table(self):
        queryset = presentations_for_update(self.teacher)

        self.assertEqual(queryset.query.select_for_update_of, ('self',))

    def test_pdf_upload_preserves_original_and_generates_slide_records(self):
        self.client.force_login(self.teacher)

        response = self.upload('lecture.pdf', make_pdf(2), 'application/pdf')

        self.assertEqual(response.status_code, 201)
        presentation = Presentation.objects.get(pk=response.json()['id'])
        self.assertEqual(presentation.file_type, Presentation.FileType.PDF)
        self.assertEqual(presentation.processing_status, Presentation.ProcessingStatus.READY)
        self.assertEqual(presentation.total_slides, 2)
        self.assertTrue(presentation.file_path.storage.exists(presentation.file_path.name))
        self.assertEqual(presentation.slides.count(), 2)
        self.assertTrue(all(slide.image_path for slide in presentation.slides.all()))
        self.assertIn('source_url', response.json())
        self.assertIn('preview_url', response.json())
        preview = self.client.get(response.json()['preview_url'])
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.headers['X-Frame-Options'], 'SAMEORIGIN')
        preview.close()

    @patch('core.presentation_processing._convert_pptx_to_pdf')
    def test_pptx_upload_converts_to_pdf_and_generates_slides(self, convert):
        pdf_content = make_pdf(3)
        convert.side_effect = lambda source, destination: Path(destination).write_bytes(pdf_content)
        self.client.force_login(self.teacher)

        response = self.upload(
            'lecture.pptx',
            make_pptx(),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

        self.assertEqual(response.status_code, 201)
        presentation = Presentation.objects.get(pk=response.json()['id'])
        self.assertEqual(presentation.file_type, Presentation.FileType.PPTX)
        self.assertEqual(presentation.processing_status, Presentation.ProcessingStatus.READY)
        self.assertEqual(presentation.total_slides, 3)
        self.assertTrue(presentation.preview_path)
        self.assertEqual(presentation.slides.count(), 3)
        convert.assert_called_once()

    @patch('core.presentation_processing._convert_pptx_to_pdf')
    def test_conversion_failure_is_recorded_without_losing_original(self, convert):
        convert.side_effect = RuntimeError('converter unavailable')
        self.client.force_login(self.teacher)

        response = self.upload(
            'lecture.pptx',
            make_pptx(),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

        self.assertEqual(response.status_code, 201)
        presentation = Presentation.objects.get(pk=response.json()['id'])
        self.assertEqual(presentation.processing_status, Presentation.ProcessingStatus.FAILED)
        self.assertIn('converter unavailable', presentation.processing_error)
        self.assertTrue(presentation.file_path.storage.exists(presentation.file_path.name))

    @patch('core.presentation_processing._convert_pptx_to_pdf')
    def test_conversion_timeout_is_recorded_and_can_be_retried(self, convert):
        convert.side_effect = subprocess.TimeoutExpired('soffice', 120)
        self.client.force_login(self.teacher)

        response = self.upload(
            'lecture.pptx',
            make_pptx(),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

        self.assertEqual(response.status_code, 201)
        presentation = Presentation.objects.get(pk=response.json()['id'])
        self.assertEqual(presentation.processing_status, Presentation.ProcessingStatus.FAILED)
        self.assertIn('timed out', presentation.processing_error)
        self.assertTrue(presentation.file_path.storage.exists(presentation.file_path.name))

    def test_repeating_upload_request_does_not_create_duplicate_presentation(self):
        self.client.force_login(self.teacher)
        request_id = uuid4()

        first = self.client.post(
            reverse('presentation-list'),
            {
                'title': 'Reliable Upload',
                'request_id': str(request_id),
                'file': SimpleUploadedFile(
                    'lecture.pdf',
                    make_pdf(1),
                    content_type='application/pdf',
                ),
            },
        )
        second = self.client.post(
            reverse('presentation-list'),
            {
                'title': 'Reliable Upload',
                'request_id': str(request_id),
                'file': SimpleUploadedFile(
                    'lecture.pdf',
                    make_pdf(1),
                    content_type='application/pdf',
                ),
            },
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['id'], first.json()['id'])
        self.assertEqual(Presentation.objects.filter(user=self.teacher).count(), 1)

    def test_failed_presentation_can_be_retried_from_preserved_original(self):
        presentation = self.create_ready_presentation()
        old_slide_paths = [slide.image_path.name for slide in presentation.slides.all()]
        storage = presentation.file_path.storage
        presentation.processing_status = Presentation.ProcessingStatus.FAILED
        presentation.processing_error = 'Temporary renderer failure.'
        presentation.save(update_fields=['processing_status', 'processing_error'])
        self.client.force_login(self.teacher)

        response = self.client.post(reverse('presentation-retry', args=[presentation.pk]))

        self.assertEqual(response.status_code, 200)
        presentation.refresh_from_db()
        self.assertEqual(presentation.processing_status, Presentation.ProcessingStatus.READY)
        self.assertEqual(presentation.processing_error, '')
        self.assertEqual(presentation.slides.count(), 2)
        self.assertTrue(all(not storage.exists(path) for path in old_slide_paths))
        self.assertTrue(SystemLog.objects.filter(
            activity__contains=f'Retried presentation {presentation.pk}',
        ).exists())

    def test_repeating_retry_after_success_returns_the_ready_presentation(self):
        presentation = self.create_ready_presentation()
        presentation.processing_status = Presentation.ProcessingStatus.FAILED
        presentation.save(update_fields=['processing_status'])
        self.client.force_login(self.teacher)

        first = self.client.post(reverse('presentation-retry', args=[presentation.pk]))
        second = self.client.post(reverse('presentation-retry', args=[presentation.pk]))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['processing_status'], 'ready')
        self.assertEqual(SystemLog.objects.filter(
            activity__contains=f'Retried presentation {presentation.pk}',
        ).count(), 1)

    def test_deleting_unused_presentation_removes_all_stored_files(self):
        presentation = self.create_ready_presentation()
        presentation.preview_path.save('preview.pdf', ContentFile(make_pdf(1)), save=True)
        storage = presentation.file_path.storage
        stored_paths = [
            presentation.file_path.name,
            presentation.preview_path.name,
            *[slide.image_path.name for slide in presentation.slides.all()],
        ]
        self.assertTrue(all(storage.exists(path) for path in stored_paths))
        self.client.force_login(self.teacher)

        response = self.client.delete(reverse('presentation-detail', args=[presentation.pk]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Presentation.objects.filter(pk=presentation.pk).exists())
        self.assertTrue(all(not storage.exists(path) for path in stored_paths))

    def test_presentation_used_by_session_cannot_be_deleted(self):
        presentation = self.create_ready_presentation()
        ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        source_path = presentation.file_path.name
        storage = presentation.file_path.storage
        self.client.force_login(self.teacher)

        response = self.client.delete(reverse('presentation-detail', args=[presentation.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Presentation.objects.filter(pk=presentation.pk).exists())
        self.assertTrue(storage.exists(source_path))
        with self.assertRaises(ProtectedError):
            presentation.delete()

    def test_presentation_lifecycle_actions_are_permission_scoped(self):
        foreign = self.create_ready_presentation(user=self.other_teacher)
        foreign.processing_status = Presentation.ProcessingStatus.FAILED
        foreign.save(update_fields=['processing_status'])
        self.client.force_login(self.teacher)

        retry = self.client.post(reverse('presentation-retry', args=[foreign.pk]))
        delete = self.client.delete(reverse('presentation-detail', args=[foreign.pk]))

        self.assertEqual(retry.status_code, 404)
        self.assertEqual(delete.status_code, 404)

    def test_presentation_list_reports_whether_a_presentation_is_in_use(self):
        unused = self.create_ready_presentation(title='Unused')
        used = self.create_ready_presentation(title='Used')
        ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=used,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('presentation-list'))

        by_id = {item['id']: item for item in response.json()}
        self.assertFalse(by_id[unused.pk]['in_use'])
        self.assertTrue(by_id[used.pk]['in_use'])

    def test_upload_rejects_unsupported_spoofed_mismatched_and_oversized_files(self):
        self.client.force_login(self.teacher)

        unsupported = self.upload('lecture.exe', b'MZ fake', 'application/octet-stream')
        spoofed = self.upload('lecture.pdf', b'not a pdf', 'application/pdf')
        wrong_mime = self.upload('lecture.pdf', make_pdf(1), 'text/plain')
        with override_settings(PRESENTATION_MAX_UPLOAD_BYTES=10):
            oversized = self.upload('lecture.pdf', make_pdf(1), 'application/pdf')
        with override_settings(PRESENTATION_MAX_EXPANDED_BYTES=100):
            expanded = self.upload(
                'lecture.pptx',
                make_pptx(expanded_payload=200),
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            )

        self.assertEqual(unsupported.status_code, 400)
        self.assertEqual(spoofed.status_code, 400)
        self.assertEqual(wrong_mime.status_code, 400)
        self.assertEqual(oversized.status_code, 400)
        self.assertEqual(expanded.status_code, 400)
        self.assertEqual(Presentation.objects.count(), 0)

    def test_pdf_over_slide_limit_is_preserved_with_failed_status(self):
        self.client.force_login(self.teacher)

        with override_settings(PRESENTATION_MAX_SLIDES=1):
            response = self.upload('too-many.pdf', make_pdf(2), 'application/pdf')

        self.assertEqual(response.status_code, 201)
        presentation = Presentation.objects.get(pk=response.json()['id'])
        self.assertEqual(presentation.processing_status, Presentation.ProcessingStatus.FAILED)
        self.assertIn('1-slide limit', presentation.processing_error)
        self.assertTrue(presentation.file_path.storage.exists(presentation.file_path.name))

    def test_presentation_lists_and_files_are_role_scoped(self):
        own = self.create_ready_presentation()
        foreign = self.create_ready_presentation(
            user=self.other_teacher,
            title='Foreign Presentation',
        )
        self.client.force_login(self.teacher)

        listed = self.client.get(reverse('presentation-list'))
        own_file = self.client.get(reverse('presentation-source', args=[own.pk]))
        foreign_file = self.client.get(reverse('presentation-source', args=[foreign.pk]))

        self.assertEqual([item['id'] for item in listed.json()], [own.pk])
        self.assertEqual(own_file.status_code, 200)
        self.assertEqual(foreign_file.status_code, 404)
        own_file.close()

    def test_organization_admin_sees_only_organization_presentations(self):
        own = self.create_ready_presentation()
        foreign = self.create_ready_presentation(user=self.other_teacher, title='Foreign Presentation')
        self.client.force_login(self.org_admin)

        org_response = self.client.get(reverse('presentation-list'))
        self.client.force_login(self.system_admin)
        system_response = self.client.get(reverse('presentation-list'))

        self.assertEqual([item['id'] for item in org_response.json()], [own.pk])
        self.assertEqual(
            {item['id'] for item in system_response.json()},
            {own.pk, foreign.pk},
        )

    def test_session_options_are_scoped_and_only_include_active_cameras(self):
        presentation = self.create_ready_presentation()
        failed = self.create_ready_presentation(title='Failed Presentation')
        failed.processing_status = Presentation.ProcessingStatus.FAILED
        failed.processing_error = 'Conversion failed.'
        failed.save(update_fields=['processing_status', 'processing_error'])
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-options'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()['subjects']], [self.subject.pk])
        self.assertEqual(
            response.json()['subjects'][0]['cameras'],
            [{
                'id': self.front_camera.pk,
                'name': self.front_camera.camera_name,
                'position': self.front_camera.position,
                'position_label': self.front_camera.get_position_display(),
                'status': self.front_camera.status,
                'status_label': self.front_camera.get_status_display(),
            }],
        )
        presentation_data = response.json()['presentations']
        self.assertEqual({item['id'] for item in presentation_data}, {presentation.pk, failed.pk})
        failed_data = next(item for item in presentation_data if item['id'] == failed.pk)
        self.assertEqual(failed_data['processing_status'], 'failed')
        self.assertEqual(failed_data['processing_error'], 'Conversion failed.')

    def test_start_session_creates_camera_links_and_initial_slide_event(self):
        presentation = self.create_ready_presentation()
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('session-list'),
            {
                'subject': self.subject.pk,
                'presentation': presentation.pk,
                'cameras': [self.front_camera.pk],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        session = ClassroomSession.objects.get(pk=response.json()['id'])
        self.assertEqual(session.user, self.teacher)
        self.assertEqual(session.session_date, timezone.localdate())
        self.assertIsNone(session.ended_at)
        self.assertEqual(list(
            SessionCamera.objects.filter(session=session).values_list('camera_id', flat=True),
        ), [self.front_camera.pk])
        expected_camera = {
            'id': self.front_camera.pk,
            'name': self.front_camera.camera_name,
            'position': self.front_camera.position,
            'position_label': self.front_camera.get_position_display(),
            'status': self.front_camera.status,
            'status_label': self.front_camera.get_status_display(),
        }
        self.assertEqual(response.json()['cameras'], [expected_camera])
        refreshed = self.client.get(reverse('session-list'))
        self.assertEqual(refreshed.json()[0]['cameras'], [expected_camera])
        self.assertEqual(session.slide_events.count(), 1)
        self.assertEqual(session.slide_events.get().slide.slide_number, 1)
        self.assertTrue(SystemLog.objects.filter(activity__contains='Started classroom session').exists())

    def test_session_can_start_without_camera_hardware(self):
        presentation = self.create_ready_presentation()
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('session-list'),
            {
                'subject': self.subject.pk,
                'presentation': presentation.pk,
                'cameras': [],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['cameras'], [])

    def test_start_session_rejects_foreign_subject_unready_presentation_and_bad_camera(self):
        ready = self.create_ready_presentation()
        failed = self.create_ready_presentation(title='Failed Presentation')
        failed.processing_status = Presentation.ProcessingStatus.FAILED
        failed.save(update_fields=['processing_status'])
        self.client.force_login(self.teacher)

        foreign_subject = self.client.post(
            reverse('session-list'),
            {'subject': self.other_subject.pk, 'presentation': ready.pk, 'cameras': []},
            content_type='application/json',
        )
        unready = self.client.post(
            reverse('session-list'),
            {'subject': self.subject.pk, 'presentation': failed.pk, 'cameras': []},
            content_type='application/json',
        )
        bad_camera = self.client.post(
            reverse('session-list'),
            {
                'subject': self.subject.pk,
                'presentation': ready.pk,
                'cameras': [self.left_camera.pk],
            },
            content_type='application/json',
        )

        self.assertEqual(foreign_subject.status_code, 400)
        self.assertIn('subject', foreign_subject.json())
        self.assertEqual(unready.status_code, 400)
        self.assertIn('presentation', unready.json())
        self.assertEqual(bad_camera.status_code, 400)
        self.assertIn('cameras', bad_camera.json())

    def test_user_cannot_start_a_second_active_session(self):
        presentation = self.create_ready_presentation()
        ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('session-list'),
            {'subject': self.subject.pk, 'presentation': presentation.pk, 'cameras': []},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.json())
        self.assertEqual(
            ClassroomSession.objects.filter(user=self.teacher, ended_at__isnull=True).count(),
            1,
        )

    def test_slide_navigation_and_end_session_are_persisted(self):
        presentation = self.create_ready_presentation()
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        second_slide = presentation.slides.get(slide_number=2)
        self.client.force_login(self.teacher)

        entered = self.client.post(
            reverse('session-enter-slide', args=[session.pk]),
            {'slide': second_slide.pk},
            content_type='application/json',
        )
        ended = self.client.post(reverse('session-end', args=[session.pk]))

        self.assertEqual(entered.status_code, 201)
        self.assertTrue(SlideEvent.objects.filter(session=session, slide=second_slide).exists())
        listed_session = self.client.get(reverse('session-list')).json()[0]
        self.assertEqual(listed_session['current_slide'], second_slide.pk)
        self.assertEqual(ended.status_code, 200)
        session.refresh_from_db()
        self.assertIsNotNone(session.ended_at)
        self.assertEqual(ended.json()['status'], 'completed')
        self.assertTrue(SystemLog.objects.filter(activity__contains='Ended classroom session').exists())

    def test_repeating_end_session_is_idempotent(self):
        presentation = self.create_ready_presentation()
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        self.client.force_login(self.teacher)

        first = self.client.post(reverse('session-end', args=[session.pk]))
        first_ended_at = first.json()['ended_at']
        second = self.client.post(reverse('session-end', args=[session.pk]))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['ended_at'], first_ended_at)
        self.assertEqual(second.json()['status'], 'completed')
        self.assertEqual(
            SystemLog.objects.filter(
                activity=f'Ended classroom session {session.pk}.',
            ).count(),
            1,
        )

    def test_repeating_same_slide_change_does_not_create_duplicate_event(self):
        presentation = self.create_ready_presentation()
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        first_slide = presentation.slides.get(slide_number=1)
        second_slide = presentation.slides.get(slide_number=2)
        SlideEvent.objects.create(
            session=session,
            slide=first_slide,
            entered_at=session.started_at,
        )
        self.client.force_login(self.teacher)

        first = self.client.post(
            reverse('session-enter-slide', args=[session.pk]),
            {'slide': second_slide.pk},
            content_type='application/json',
        )
        second = self.client.post(
            reverse('session-enter-slide', args=[session.pk]),
            {'slide': second_slide.pk},
            content_type='application/json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertTrue(first.json()['created'])
        self.assertFalse(second.json()['created'])
        self.assertEqual(session.slide_events.filter(slide=second_slide).count(), 1)

    def test_active_session_response_restores_saved_slide_and_linked_cameras(self):
        presentation = self.create_ready_presentation()
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        second_slide = presentation.slides.get(slide_number=2)
        SessionCamera.objects.create(session=session, camera=self.front_camera)
        SlideEvent.objects.create(
            session=session,
            slide=second_slide,
            entered_at=timezone.now(),
        )
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-list'))

        self.assertEqual(response.status_code, 200)
        restored = response.json()[0]
        self.assertEqual(restored['status'], 'ongoing')
        self.assertEqual(restored['current_slide'], second_slide.pk)
        self.assertEqual([camera['id'] for camera in restored['cameras']], [self.front_camera.pk])

    def test_other_teacher_cannot_control_session(self):
        presentation = self.create_ready_presentation()
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        self.client.force_login(self.other_teacher)

        ended = self.client.post(reverse('session-end', args=[session.pk]))

        self.assertEqual(ended.status_code, 404)

    def test_session_lists_are_scoped_for_teacher_org_admin_and_system_admin(self):
        presentation = self.create_ready_presentation()
        other_presentation = self.create_ready_presentation(
            user=self.other_teacher,
            title='Foreign Presentation',
        )
        own_session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        foreign_session = ClassroomSession.objects.create(
            user=self.other_teacher,
            subject=self.other_subject,
            presentation=other_presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        self.client.force_login(self.teacher)
        teacher_response = self.client.get(reverse('session-list'))
        self.client.force_login(self.org_admin)
        org_response = self.client.get(reverse('session-list'))
        self.client.force_login(self.system_admin)
        system_response = self.client.get(reverse('session-list'))

        self.assertEqual([item['id'] for item in teacher_response.json()], [own_session.pk])
        self.assertEqual([item['id'] for item in org_response.json()], [own_session.pk])
        self.assertEqual(
            {item['id'] for item in system_response.json()},
            {own_session.pk, foreign_session.pk},
        )

    def test_upload_and_session_mutations_require_csrf(self):
        presentation = self.create_ready_presentation()
        failed_presentation = self.create_ready_presentation(title='Failed')
        failed_presentation.processing_status = Presentation.ProcessingStatus.FAILED
        failed_presentation.save(update_fields=['processing_status'])
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.teacher)

        upload = csrf_client.post(
            reverse('presentation-list'),
            {
                'title': 'CSRF Lecture',
                'file': SimpleUploadedFile('lecture.pdf', make_pdf(1), content_type='application/pdf'),
            },
        )
        start = csrf_client.post(
            reverse('session-list'),
            {'subject': self.subject.pk, 'presentation': presentation.pk, 'cameras': []},
            content_type='application/json',
        )
        retry = csrf_client.post(reverse('presentation-retry', args=[failed_presentation.pk]))
        delete = csrf_client.delete(reverse('presentation-detail', args=[presentation.pk]))

        self.assertEqual(upload.status_code, 403)
        self.assertEqual(start.status_code, 403)
        self.assertEqual(retry.status_code, 403)
        self.assertEqual(delete.status_code, 403)
        self.assertTrue(Presentation.objects.filter(pk=presentation.pk).exists())

    def test_anonymous_user_cannot_access_presentations_or_sessions(self):
        presentation_response = self.client.get(reverse('presentation-list'))
        session_response = self.client.get(reverse('session-list'))

        self.assertIn(presentation_response.status_code, (401, 403))
        self.assertIn(session_response.status_code, (401, 403))
