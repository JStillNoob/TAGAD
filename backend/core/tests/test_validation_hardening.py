from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from ..models import Classroom, Organization, Subject


User = get_user_model()


class ValidationHardeningTests(TestCase):
    password = 'A-strong-validation-password-2026!'

    def setUp(self):
        self.organization = Organization.objects.create(
            organization_name='TAGAD University',
            organization_code='TAGAD-U',
        )
        self.admin = User.objects.create_superuser(
            username='system.admin',
            email='system.admin@example.com',
            password=self.password,
            role=User.Role.SYSTEM_ADMIN,
            status=User.Status.ACTIVE,
        )
        self.teacher = User.objects.create_user(
            username='teacher.one',
            email='teacher.one@example.com',
            first_name='Teacher',
            last_name='One',
            organization=self.organization,
            password=self.password,
            role=User.Role.TEACHER,
            status=User.Status.ACTIVE,
        )
        self.org_admin = User.objects.create_user(
            username='organization.admin',
            email='organization.admin@example.com',
            first_name='Organization',
            last_name='Admin',
            organization=self.organization,
            password=self.password,
            role=User.Role.ORG_ADMIN,
            status=User.Status.ACTIVE,
        )

    def registration_payload(self, **overrides):
        return {
            'username': '  teacher.two  ',
            'email': '  TEACHER.TWO@EXAMPLE.COM  ',
            'first_name': '  Teacher  ',
            'last_name': '  Two  ',
            'middle_name': '',
            'contact_no': '  +63 (917) 123-4567  ',
            'organization_code': '  tagad-u  ',
            'password': self.password,
            'password_confirmation': self.password,
            **overrides,
        }

    def test_registration_normalizes_identity_and_accepts_flexible_phone_format(self):
        response = self.client.post(
            reverse('register'),
            self.registration_payload(),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.json())
        user = User.objects.get(username='teacher.two')
        self.assertEqual(user.email, 'teacher.two@example.com')
        self.assertEqual(user.first_name, 'Teacher')
        self.assertEqual(user.last_name, 'Two')
        self.assertEqual(user.contact_no, '+63 (917) 123-4567')
        self.assertEqual(user.organization, self.organization)

    def test_user_workflows_reject_invalid_contact_numbers(self):
        registration = self.client.post(
            reverse('register'),
            self.registration_payload(contact_no='call me maybe'),
            content_type='application/json',
        )
        self.client.force_login(self.admin)
        managed_user = self.client.post(
            reverse('user-list'),
            {
                'username': 'teacher.three',
                'email': 'teacher.three@example.com',
                'first_name': 'Teacher',
                'last_name': 'Three',
                'contact_no': '123',
                'role': User.Role.TEACHER,
                'status': User.Status.ACTIVE,
                'organization': self.organization.pk,
                'password': self.password,
            },
            content_type='application/json',
        )

        self.assertEqual(registration.status_code, 400)
        self.assertIn('contact_no', registration.json())
        self.assertEqual(managed_user.status_code, 400)
        self.assertIn('contact_no', managed_user.json())

    def test_profile_and_organization_settings_validate_contact_fields(self):
        self.client.force_login(self.teacher)
        profile = self.client.patch(
            reverse('profile-settings'),
            {'contact_no': 'not-a-number'},
            content_type='application/json',
        )
        self.client.force_login(self.org_admin)
        organization = self.client.patch(
            reverse('organization-settings'),
            {'contact_no': '12'},
            content_type='application/json',
        )

        self.assertEqual(profile.status_code, 400)
        self.assertIn('contact_no', profile.json())
        self.assertEqual(organization.status_code, 400)
        self.assertIn('contact_no', organization.json())

    def test_classroom_and_subject_codes_are_normalized_and_capacity_is_bounded(self):
        self.client.force_login(self.admin)
        classroom = self.client.post(
            reverse('classroom-list'),
            {
                'organization': self.organization.pk,
                'room_code': '  room-101  ',
                'building': '  Main Building  ',
                'capacity': 40,
            },
            content_type='application/json',
        )
        subject = self.client.post(
            reverse('subject-list'),
            {
                'classroom': classroom.json()['id'],
                'teacher': self.teacher.pk,
                'subject_code': '  cce-101  ',
                'subject_name': '  Introduction to Computing  ',
            },
            content_type='application/json',
        )
        excessive_capacity = self.client.post(
            reverse('classroom-list'),
            {
                'organization': self.organization.pk,
                'room_code': 'ROOM-OVERFLOW',
                'capacity': 10001,
            },
            content_type='application/json',
        )
        invalid_code = self.client.post(
            reverse('classroom-list'),
            {
                'organization': self.organization.pk,
                'room_code': 'ROOM<script>',
                'capacity': 40,
            },
            content_type='application/json',
        )

        self.assertEqual(classroom.status_code, 201, classroom.json())
        self.assertEqual(classroom.json()['room_code'], 'ROOM-101')
        self.assertEqual(classroom.json()['building'], 'Main Building')
        self.assertEqual(subject.status_code, 201, subject.json())
        self.assertEqual(subject.json()['subject_code'], 'CCE-101')
        self.assertEqual(subject.json()['subject_name'], 'Introduction to Computing')
        self.assertEqual(excessive_capacity.status_code, 400)
        self.assertIn('capacity', excessive_capacity.json())
        self.assertEqual(invalid_code.status_code, 400)
        self.assertIn('room_code', invalid_code.json())

    def test_quick_setup_applies_the_same_normalization_and_validation(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('class-management-quick-setup'),
            {
                'classroom': {
                    'organization': self.organization.pk,
                    'room_code': '  lab-202  ',
                    'building': '  Technology Center  ',
                    'capacity': 50,
                },
                'cameras': [{'camera_name': '  Front Camera  ', 'position': 'front'}],
                'subject': {
                    'subject_code': '  cce-202  ',
                    'subject_name': '  Systems Analysis  ',
                    'teacher': self.teacher.pk,
                },
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['classroom']['room_code'], 'LAB-202')
        self.assertEqual(response.json()['cameras'][0]['camera_name'], 'Front Camera')
        self.assertEqual(response.json()['subject']['subject_code'], 'CCE-202')

    def test_database_rejects_case_only_duplicate_business_codes(self):
        Classroom.objects.create(organization=self.organization, room_code='ROOM-ONE')
        classroom = Classroom.objects.create(
            organization=self.organization,
            room_code='ROOM-TWO',
        )
        Subject.objects.create(
            classroom=classroom,
            teacher=self.teacher,
            subject_code='SUBJECT-ONE',
            subject_name='Subject One',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Organization.objects.create(
                organization_name='Duplicate Organization',
                organization_code='tagad-u',
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Classroom.objects.create(
                organization=self.organization,
                room_code='room-one',
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subject.objects.create(
                classroom=classroom,
                teacher=self.teacher,
                subject_code='subject-one',
                subject_name='Duplicate Subject',
            )

    def test_direct_model_creation_normalizes_business_codes(self):
        organization = Organization.objects.create(
            organization_name='Lowercase Organization',
            organization_code='  lower-org  ',
        )
        classroom = Classroom.objects.create(
            organization=organization,
            room_code='  lower-room  ',
        )
        subject = Subject.objects.create(
            classroom=classroom,
            teacher=self.teacher,
            subject_code='  lower-subject  ',
            subject_name='Lowercase Subject',
        )

        self.assertEqual(organization.organization_code, 'LOWER-ORG')
        self.assertEqual(classroom.room_code, 'LOWER-ROOM')
        self.assertEqual(subject.subject_code, 'LOWER-SUBJECT')
