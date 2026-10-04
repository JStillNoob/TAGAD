from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Camera,
    Classroom,
    ClassroomSession,
    Organization,
    Presentation,
    Report,
    Subject,
    SystemLog,
)


User = get_user_model()


class RecordLifecycleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='Lifecycle College',
            organization_code='LIFE',
        )
        self.other_organization = Organization.objects.create(
            organization_name='Other College',
            organization_code='OTHER',
        )
        self.admin = User.objects.create_user(
            username='lifecycle.admin',
            email='lifecycle.admin@example.test',
            password='StrongPass123!',
            role=User.Role.SYSTEM_ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )
        self.teacher = User.objects.create_user(
            username='lifecycle.teacher',
            email='lifecycle.teacher@example.test',
            password='StrongPass123!',
            organization=self.organization,
            role=User.Role.TEACHER,
            status=User.Status.ACTIVE,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='LIFE-101',
            capacity=30,
        )
        self.subject = Subject.objects.create(
            classroom=self.classroom,
            teacher=self.teacher,
            subject_code='LIFE-1',
            subject_name='Lifecycle Safety',
        )
        self.camera = Camera.objects.create(
            classroom=self.classroom,
            camera_name='Lifecycle Front',
            position=Camera.Position.FRONT,
        )
        self.presentation = Presentation.objects.create(
            user=self.teacher,
            title='Lifecycle Slides',
            file_name='lifecycle.pdf',
            file_path='presentations/lifecycle.pdf',
            processing_status=Presentation.ProcessingStatus.READY,
        )
        self.completed_session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=self.presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now() - timedelta(hours=1),
            ended_at=timezone.now(),
        )
        self.client.force_login(self.admin)

    def test_classroom_archive_filter_restore_and_audit(self):
        response = self.client.delete(reverse('classroom-detail', args=[self.classroom.pk]))

        self.assertEqual(response.status_code, 204)
        self.classroom.refresh_from_db()
        self.assertTrue(self.classroom.is_archived)
        active_ids = {
            item['id'] for item in self.client.get(reverse('classroom-list')).json()['results']
        }
        archived = self.client.get(reverse('classroom-list'), {'lifecycle': 'archived'}).json()
        self.assertNotIn(self.classroom.pk, active_ids)
        self.assertEqual([item['id'] for item in archived['results']], [self.classroom.pk])
        self.assertTrue(archived['results'][0]['is_archived'])

        restored = self.client.post(reverse('classroom-restore', args=[self.classroom.pk]))

        self.assertEqual(restored.status_code, 200)
        self.classroom.refresh_from_db()
        self.assertFalse(self.classroom.is_archived)
        self.assertTrue(SystemLog.objects.filter(activity__contains='Restored classroom').exists())

    def test_subject_and_camera_with_history_archive_instead_of_delete(self):
        subject_response = self.client.delete(reverse('subject-detail', args=[self.subject.pk]))
        camera_response = self.client.delete(reverse('camera-detail', args=[self.camera.pk]))

        self.assertEqual(subject_response.status_code, 204)
        self.assertEqual(camera_response.status_code, 204)
        self.subject.refresh_from_db()
        self.camera.refresh_from_db()
        self.assertTrue(self.subject.is_archived)
        self.assertTrue(self.camera.is_archived)
        self.assertTrue(ClassroomSession.objects.filter(pk=self.completed_session.pk).exists())

        self.assertEqual(
            self.client.post(reverse('subject-restore', args=[self.subject.pk])).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(reverse('camera-restore', args=[self.camera.pk])).status_code,
            200,
        )

    def test_active_session_blocks_related_archiving(self):
        active_session = ClassroomSession.objects.create(
            user=self.admin,
            subject=self.subject,
            presentation=self.presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        active_session.session_cameras.create(camera=self.camera)

        self.assertEqual(
            self.client.delete(reverse('classroom-detail', args=[self.classroom.pk])).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(reverse('subject-detail', args=[self.subject.pk])).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(reverse('camera-detail', args=[self.camera.pk])).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(reverse('presentation-detail', args=[self.presentation.pk])).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(reverse('session-lifecycle', args=[active_session.pk])).status_code,
            400,
        )

    def test_used_presentation_is_archived_and_restored_without_removing_files(self):
        response = self.client.delete(reverse('presentation-detail', args=[self.presentation.pk]))

        self.assertEqual(response.status_code, 204)
        self.presentation.refresh_from_db()
        self.assertTrue(self.presentation.is_archived)
        self.assertEqual(self.presentation.file_path.name, 'presentations/lifecycle.pdf')
        self.assertNotContains(self.client.get(reverse('presentation-list')), 'Lifecycle Slides')

        restored = self.client.post(reverse('presentation-restore', args=[self.presentation.pk]))

        self.assertEqual(restored.status_code, 200)
        self.presentation.refresh_from_db()
        self.assertFalse(self.presentation.is_archived)

    def test_archived_records_are_rejected_for_new_sessions(self):
        self.subject.archived_at = timezone.now()
        self.subject.archived_by = self.admin
        self.subject.save(update_fields=['archived_at', 'archived_by'])
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('session-list'),
            {
                'subject': self.subject.pk,
                'presentation': self.presentation.pk,
                'cameras': [],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('subject', response.json())

    def test_archived_camera_is_removed_from_session_subject_choices(self):
        self.camera.archived_at = timezone.now()
        self.camera.archived_by = self.admin
        self.camera.save(update_fields=['archived_at', 'archived_by'])
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('session-subject-list'))

        self.assertEqual(response.status_code, 200)
        subject = next(
            item for item in response.json()['results']
            if item['id'] == self.subject.pk
        )
        self.assertEqual(subject['cameras'], [])

    def test_child_records_cannot_be_restored_under_archived_classroom(self):
        archived_at = timezone.now()
        self.classroom.archived_at = archived_at
        self.classroom.archived_by = self.admin
        self.classroom.save(update_fields=['archived_at', 'archived_by'])
        self.subject.archived_at = archived_at
        self.subject.archived_by = self.admin
        self.subject.save(update_fields=['archived_at', 'archived_by'])
        self.camera.archived_at = archived_at
        self.camera.archived_by = self.admin
        self.camera.save(update_fields=['archived_at', 'archived_by'])

        subject = self.client.post(reverse('subject-restore', args=[self.subject.pk]))
        camera = self.client.post(reverse('camera-restore', args=[self.camera.pk]))

        self.assertEqual(subject.status_code, 400)
        self.assertEqual(camera.status_code, 400)

    def test_completed_session_can_be_archived_restored_and_still_opened_directly(self):
        archived = self.client.delete(
            reverse('session-lifecycle', args=[self.completed_session.pk]),
        )

        self.assertEqual(archived.status_code, 204)
        active_ids = {
            item['id'] for item in self.client.get(reverse('session-list')).json()['results']
        }
        self.assertNotIn(self.completed_session.pk, active_ids)
        self.assertEqual(
            self.client.get(
                reverse('session-analytics', args=[self.completed_session.pk]),
            ).status_code,
            200,
        )

        restored = self.client.post(
            reverse('session-lifecycle', args=[self.completed_session.pk]),
        )
        self.assertEqual(restored.status_code, 200)

    def test_organization_archive_blocks_active_sessions_and_is_reversible(self):
        teacher_client = Client()
        teacher_client.force_login(self.teacher)
        self.assertEqual(teacher_client.get(reverse('current-user')).status_code, 200)
        active_session = ClassroomSession.objects.create(
            user=self.admin,
            subject=self.subject,
            presentation=self.presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )
        url = reverse('organization-lifecycle', args=[self.organization.pk])
        self.assertEqual(self.client.delete(url).status_code, 400)
        active_session.ended_at = timezone.now()
        active_session.save(update_fields=['ended_at'])

        self.assertEqual(self.client.delete(url).status_code, 204)
        self.organization.refresh_from_db()
        self.assertTrue(self.organization.is_archived)
        self.assertEqual(self.organization.status, Organization.Status.INACTIVE)
        self.assertEqual(teacher_client.get(reverse('current-user')).status_code, 403)
        organization_ids = {
            item['id'] for item in self.client.get(
                reverse('organization-list'),
                {'lifecycle': 'archived'},
            ).json()['results']
        }
        self.assertIn(self.organization.pk, organization_ids)

        self.assertEqual(self.client.post(url).status_code, 200)
        self.organization.refresh_from_db()
        self.assertFalse(self.organization.is_archived)
        self.assertEqual(self.organization.status, Organization.Status.ACTIVE)

    def test_org_admin_cannot_manage_organization_lifecycle(self):
        org_admin = User.objects.create_user(
            username='organization.admin',
            email='organization.admin@example.test',
            password='StrongPass123!',
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
            status=User.Status.ACTIVE,
        )
        self.client.force_login(org_admin)

        self.assertEqual(self.client.get(reverse('organization-list')).status_code, 403)
        self.assertEqual(
            self.client.delete(
                reverse('organization-lifecycle', args=[self.organization.pk]),
            ).status_code,
            403,
        )

    def test_deactivation_invalidates_existing_login_session(self):
        teacher_client = Client()
        teacher_client.force_login(self.teacher)
        self.assertEqual(teacher_client.get(reverse('current-user')).status_code, 200)

        response = self.client.delete(reverse('user-detail', args=[self.teacher.pk]))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(teacher_client.get(reverse('current-user')).status_code, 403)

    def test_account_with_active_classroom_session_cannot_be_deactivated(self):
        active_session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=self.presentation,
            session_date=timezone.localdate(),
            started_at=timezone.now(),
        )

        response = self.client.delete(reverse('user-detail', args=[self.teacher.pk]))

        self.assertEqual(response.status_code, 400)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_active)
        self.assertIsNone(active_session.ended_at)

    def test_generated_report_can_be_deleted_without_deleting_session(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            path = default_storage.save(
                'reports/lifecycle/report.pdf',
                ContentFile(b'report'),
            )
            report = Report.objects.create(
                session=self.completed_session,
                generated_by=self.teacher,
                report_type='pdf',
                report_path=path,
            )

            response = self.client.delete(reverse('report-detail', args=[report.pk]))

            self.assertEqual(response.status_code, 204)
            self.assertFalse(Report.objects.filter(pk=report.pk).exists())
            self.assertFalse(default_storage.exists(path))
            self.assertTrue(ClassroomSession.objects.filter(pk=self.completed_session.pk).exists())

    def test_invalid_lifecycle_filter_is_rejected(self):
        response = self.client.get(reverse('classroom-list'), {'lifecycle': 'deleted'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('lifecycle', response.json())
