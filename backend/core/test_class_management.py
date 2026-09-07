from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Camera,
    Classroom,
    ClassroomSession,
    Organization,
    Presentation,
    SessionCamera,
    Subject,
    SystemLog,
)


User = get_user_model()


class ClassManagementTests(TestCase):
    password = 'A-strong-class-management-password-2026'

    def setUp(self):
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
            password=self.password,
            role=User.Role.SYSTEM_ADMIN,
        )
        self.org_admin = User.objects.create_user(
            username='org.admin',
            email='org.admin@example.com',
            password=self.password,
            organization=self.organization,
            role=User.Role.ORG_ADMIN,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            email='teacher.one@example.com',
            password=self.password,
            organization=self.organization,
            role=User.Role.TEACHER,
        )
        self.other_teacher = User.objects.create_user(
            username='teacher.other',
            email='teacher.other@example.com',
            password=self.password,
            organization=self.other_organization,
            role=User.Role.TEACHER,
        )
        self.classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-101',
            building='Main Building',
            capacity=40,
        )
        self.other_classroom = Classroom.objects.create(
            organization=self.other_organization,
            room_code='ROOM-201',
            building='Other Building',
            capacity=30,
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

    def classroom_payload(self, **overrides):
        payload = {
            'organization': self.organization.pk,
            'room_code': 'ROOM-102',
            'building': 'Annex Building',
            'capacity': 35,
        }
        payload.update(overrides)
        return payload

    def subject_payload(self, **overrides):
        payload = {
            'classroom': self.classroom.pk,
            'teacher': self.teacher.pk,
            'subject_code': 'IT-302',
            'subject_name': 'Database Management',
        }
        payload.update(overrides)
        return payload

    def camera_payload(self, **overrides):
        payload = {
            'classroom': self.classroom.pk,
            'camera_name': 'Front Camera',
            'position': 'front',
            'status': 'active',
        }
        payload.update(overrides)
        return payload

    def test_system_admin_lists_all_classrooms_and_subjects(self):
        self.client.force_login(self.system_admin)

        classrooms = self.client.get(reverse('classroom-list'))
        subjects = self.client.get(reverse('subject-list'))

        self.assertEqual(classrooms.status_code, 200)
        self.assertEqual(subjects.status_code, 200)
        self.assertEqual(
            {item['id'] for item in classrooms.json()},
            {self.classroom.pk, self.other_classroom.pk},
        )
        self.assertEqual(
            {item['id'] for item in subjects.json()},
            {self.subject.pk, self.other_subject.pk},
        )

    def test_org_admin_is_scoped_to_own_organization(self):
        self.client.force_login(self.org_admin)

        classrooms = self.client.get(reverse('classroom-list'))
        subjects = self.client.get(reverse('subject-list'))

        self.assertEqual([item['id'] for item in classrooms.json()], [self.classroom.pk])
        self.assertEqual([item['id'] for item in subjects.json()], [self.subject.pk])
        self.assertEqual(
            self.client.patch(
                reverse('classroom-detail', args=[self.other_classroom.pk]),
                {'building': 'Forbidden'},
                content_type='application/json',
            ).status_code,
            404,
        )

    def test_teacher_sees_only_assigned_subjects_and_related_classrooms(self):
        second_classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-103',
        )
        self.client.force_login(self.teacher)

        classrooms = self.client.get(reverse('classroom-list'))
        subjects = self.client.get(reverse('subject-list'))

        self.assertEqual([item['id'] for item in classrooms.json()], [self.classroom.pk])
        self.assertNotIn(second_classroom.pk, [item['id'] for item in classrooms.json()])
        self.assertEqual([item['id'] for item in subjects.json()], [self.subject.pk])

    def test_teacher_and_anonymous_user_cannot_mutate_classes(self):
        self.client.force_login(self.teacher)
        teacher_create = self.client.post(
            reverse('classroom-list'),
            self.classroom_payload(),
            content_type='application/json',
        )
        teacher_update = self.client.patch(
            reverse('subject-detail', args=[self.subject.pk]),
            {'subject_name': 'Forbidden'},
            content_type='application/json',
        )
        self.client.logout()
        anonymous_list = self.client.get(reverse('classroom-list'))

        self.assertEqual(teacher_create.status_code, 403)
        self.assertEqual(teacher_update.status_code, 403)
        self.assertIn(anonymous_list.status_code, (401, 403))

    def test_org_admin_creates_classroom_in_own_organization_and_logs_it(self):
        self.client.force_login(self.org_admin)

        response = self.client.post(
            reverse('classroom-list'),
            self.classroom_payload(),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        classroom = Classroom.objects.get(pk=response.json()['id'])
        self.assertEqual(classroom.organization, self.organization)
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Created classroom',
        ).exists())

    def test_classroom_validation_rejects_bad_capacity_and_duplicate_code(self):
        self.client.force_login(self.system_admin)

        bad_capacity = self.client.post(
            reverse('classroom-list'),
            self.classroom_payload(capacity=0),
            content_type='application/json',
        )
        duplicate_code = self.client.post(
            reverse('classroom-list'),
            self.classroom_payload(room_code=self.classroom.room_code.lower()),
            content_type='application/json',
        )

        self.assertEqual(bad_capacity.status_code, 400)
        self.assertIn('capacity', bad_capacity.json())
        self.assertEqual(duplicate_code.status_code, 400)
        self.assertIn('room_code', duplicate_code.json())

    def test_classroom_with_dependencies_cannot_be_deleted(self):
        self.client.force_login(self.system_admin)

        subject_response = self.client.delete(
            reverse('classroom-detail', args=[self.classroom.pk]),
        )
        self.subject.delete()
        Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position='front',
        )
        camera_response = self.client.delete(
            reverse('classroom-detail', args=[self.classroom.pk]),
        )

        self.assertEqual(subject_response.status_code, 400)
        self.assertIn('detail', subject_response.json())
        self.assertEqual(camera_response.status_code, 400)
        self.assertTrue(Classroom.objects.filter(pk=self.classroom.pk).exists())

    def test_classroom_with_dependencies_cannot_change_organization(self):
        self.client.force_login(self.system_admin)

        response = self.client.patch(
            reverse('classroom-detail', args=[self.classroom.pk]),
            {'organization': self.other_organization.pk},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('organization', response.json())
        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.organization, self.organization)

    def test_empty_classroom_can_be_deleted_and_is_logged(self):
        empty = Classroom.objects.create(
            organization=self.organization,
            room_code='EMPTY-ROOM',
        )
        self.client.force_login(self.org_admin)

        response = self.client.delete(reverse('classroom-detail', args=[empty.pk]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Classroom.objects.filter(pk=empty.pk).exists())
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Deleted classroom',
        ).exists())

    def test_subject_teacher_must_belong_to_classroom_organization(self):
        self.client.force_login(self.system_admin)

        response = self.client.post(
            reverse('subject-list'),
            self.subject_payload(teacher=self.other_teacher.pk),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('teacher', response.json())

    def test_org_admin_cannot_create_subject_in_another_organization(self):
        self.client.force_login(self.org_admin)

        response = self.client.post(
            reverse('subject-list'),
            self.subject_payload(
                classroom=self.other_classroom.pk,
                teacher=self.other_teacher.pk,
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('classroom', response.json())

    def test_org_admin_creates_updates_and_logs_subject(self):
        self.client.force_login(self.org_admin)

        created = self.client.post(
            reverse('subject-list'),
            self.subject_payload(),
            content_type='application/json',
        )
        updated = self.client.patch(
            reverse('subject-detail', args=[created.json()['id']]),
            {'subject_name': 'Updated Database Management'},
            content_type='application/json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['subject_name'], 'Updated Database Management')
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Created subject',
        ).exists())
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Updated subject',
        ).exists())

    def test_subject_validation_rejects_duplicate_code(self):
        self.client.force_login(self.system_admin)

        response = self.client.post(
            reverse('subject-list'),
            self.subject_payload(subject_code=self.subject.subject_code.lower()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('subject_code', response.json())

    def test_subject_with_session_history_cannot_be_deleted(self):
        presentation = Presentation.objects.create(
            user=self.teacher,
            title='Lecture',
            file_name='lecture.pptx',
            file_path='/tmp/lecture.pptx',
            total_slides=10,
        )
        ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=date(2026, 9, 7),
            started_at=timezone.now(),
        )
        self.client.force_login(self.org_admin)

        response = self.client.delete(reverse('subject-detail', args=[self.subject.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Subject.objects.filter(pk=self.subject.pk).exists())

    def test_subject_without_history_can_be_deleted(self):
        self.client.force_login(self.org_admin)

        response = self.client.delete(reverse('subject-detail', args=[self.subject.pk]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Subject.objects.filter(pk=self.subject.pk).exists())

    def test_class_options_are_scoped_by_role(self):
        self.client.force_login(self.system_admin)
        system_options = self.client.get(reverse('class-management-options')).json()

        self.client.force_login(self.org_admin)
        org_options = self.client.get(reverse('class-management-options')).json()

        self.client.force_login(self.teacher)
        teacher_options = self.client.get(reverse('class-management-options')).json()

        self.assertEqual(
            {item['id'] for item in system_options['organizations']},
            {self.organization.pk, self.other_organization.pk},
        )
        self.assertEqual(
            {item['id'] for item in system_options['teachers']},
            {self.teacher.pk, self.other_teacher.pk},
        )
        self.assertEqual(org_options['organizations'], [{
            'id': self.organization.pk,
            'name': self.organization.organization_name,
        }])
        self.assertEqual([item['id'] for item in org_options['teachers']], [self.teacher.pk])
        self.assertEqual(teacher_options['organizations'], [])
        self.assertEqual(teacher_options['teachers'], [])

    def test_class_mutations_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.org_admin)

        response = csrf_client.post(
            reverse('classroom-list'),
            self.classroom_payload(),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_camera_lists_are_scoped_for_each_role(self):
        camera = Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position='front',
        )
        other_camera = Camera.objects.create(
            classroom=self.other_classroom,
            camera_name='Other Front Camera',
            position='front',
        )

        self.client.force_login(self.system_admin)
        system_response = self.client.get(reverse('camera-list'))
        self.client.force_login(self.org_admin)
        org_response = self.client.get(reverse('camera-list'))
        self.client.force_login(self.teacher)
        teacher_response = self.client.get(reverse('camera-list'))

        self.assertEqual(
            {item['id'] for item in system_response.json()},
            {camera.pk, other_camera.pk},
        )
        self.assertEqual([item['id'] for item in org_response.json()], [camera.pk])
        self.assertEqual([item['id'] for item in teacher_response.json()], [camera.pk])

    def test_org_admin_creates_and_updates_camera_with_audit_logs(self):
        self.client.force_login(self.org_admin)

        created = self.client.post(
            reverse('camera-list'),
            self.camera_payload(),
            content_type='application/json',
        )
        updated = self.client.patch(
            reverse('camera-detail', args=[created.json()['id']]),
            {'camera_name': 'Main Front Camera', 'status': 'inactive'},
            content_type='application/json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['classroom_room_code'], self.classroom.room_code)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['camera_name'], 'Main Front Camera')
        self.assertEqual(updated.json()['status'], 'inactive')
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Created camera',
        ).exists())
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Updated camera',
        ).exists())

    def test_org_admin_cannot_create_or_update_camera_in_another_organization(self):
        foreign_camera = Camera.objects.create(
            classroom=self.other_classroom,
            camera_name='Foreign Camera',
            position='front',
        )
        self.client.force_login(self.org_admin)

        create_response = self.client.post(
            reverse('camera-list'),
            self.camera_payload(classroom=self.other_classroom.pk),
            content_type='application/json',
        )
        update_response = self.client.patch(
            reverse('camera-detail', args=[foreign_camera.pk]),
            {'camera_name': 'Forbidden'},
            content_type='application/json',
        )

        self.assertEqual(create_response.status_code, 400)
        self.assertIn('classroom', create_response.json())
        self.assertEqual(update_response.status_code, 404)

    def test_teacher_and_anonymous_user_cannot_mutate_cameras(self):
        self.client.force_login(self.teacher)
        teacher_response = self.client.post(
            reverse('camera-list'),
            self.camera_payload(),
            content_type='application/json',
        )
        self.client.logout()
        anonymous_response = self.client.get(reverse('camera-list'))

        self.assertEqual(teacher_response.status_code, 403)
        self.assertIn(anonymous_response.status_code, (401, 403))

    def test_camera_validation_enforces_position_and_unique_slot(self):
        Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position='front',
        )
        self.client.force_login(self.system_admin)

        bad_position = self.client.post(
            reverse('camera-list'),
            self.camera_payload(camera_name='Ceiling Camera', position='ceiling'),
            content_type='application/json',
        )
        duplicate_name = self.client.post(
            reverse('camera-list'),
            self.camera_payload(camera_name='front camera', position='left'),
            content_type='application/json',
        )
        duplicate_position = self.client.post(
            reverse('camera-list'),
            self.camera_payload(camera_name='Another Camera', position='front'),
            content_type='application/json',
        )

        self.assertEqual(bad_position.status_code, 400)
        self.assertIn('position', bad_position.json())
        self.assertEqual(duplicate_name.status_code, 400)
        self.assertIn('camera_name', duplicate_name.json())
        self.assertEqual(duplicate_position.status_code, 400)
        self.assertIn('position', duplicate_position.json())

    def test_database_enforces_camera_name_and_position_uniqueness(self):
        Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position='front',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Camera.objects.create(
                classroom=self.classroom,
                camera_name='front camera',
                position='left',
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Camera.objects.create(
                classroom=self.classroom,
                camera_name='Different Camera',
                position='front',
            )

    def test_unused_camera_can_be_deleted_but_session_camera_is_protected(self):
        camera = Camera.objects.create(
            classroom=self.classroom,
            camera_name='Front Camera',
            position='front',
        )
        self.client.force_login(self.org_admin)
        unused_response = self.client.delete(reverse('camera-detail', args=[camera.pk]))

        protected_camera = Camera.objects.create(
            classroom=self.classroom,
            camera_name='Left Camera',
            position='left',
        )
        presentation = Presentation.objects.create(
            user=self.teacher,
            title='Camera Lecture',
            file_name='camera.pptx',
            file_path='/tmp/camera.pptx',
            total_slides=5,
        )
        session = ClassroomSession.objects.create(
            user=self.teacher,
            subject=self.subject,
            presentation=presentation,
            session_date=date(2026, 9, 7),
            started_at=timezone.now(),
        )
        SessionCamera.objects.create(session=session, camera=protected_camera)
        protected_response = self.client.delete(
            reverse('camera-detail', args=[protected_camera.pk]),
        )

        self.assertEqual(unused_response.status_code, 204)
        self.assertFalse(Camera.objects.filter(pk=camera.pk).exists())
        self.assertEqual(protected_response.status_code, 400)
        self.assertTrue(Camera.objects.filter(pk=protected_camera.pk).exists())
        self.assertTrue(SystemLog.objects.filter(
            user=self.org_admin,
            activity__contains='Deleted camera',
        ).exists())

    def test_class_options_include_camera_choices(self):
        self.client.force_login(self.org_admin)

        response = self.client.get(reverse('class-management-options'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['camera_positions'], [
            {'value': 'front', 'label': 'Front'},
            {'value': 'left', 'label': 'Left'},
            {'value': 'right', 'label': 'Right'},
        ])
        self.assertEqual(response.json()['camera_statuses'], [
            {'value': 'active', 'label': 'Active'},
            {'value': 'inactive', 'label': 'Inactive'},
        ])
