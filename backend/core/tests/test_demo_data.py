from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase

from core.models import Camera, Classroom, Organization, Subject, User


class SeedDemoCommandTests(TestCase):
    def test_command_rejects_a_weak_demo_password(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', password='password')

    def test_command_is_repeatable_and_creates_usable_demo_accounts(self):
        output = StringIO()

        call_command('seed_demo', password='DemoPassword!19', stdout=output)
        call_command('seed_demo', password='DemoPassword!19', stdout=output)

        self.assertEqual(Organization.objects.filter(organization_code='TAGAD-DEMO').count(), 1)
        self.assertEqual(Classroom.objects.filter(room_code='DEMO-101').count(), 1)
        self.assertEqual(Subject.objects.filter(subject_code='DEMO-IT101').count(), 1)
        self.assertEqual(Camera.objects.filter(camera_name='Demo Front Camera').count(), 1)
        administrator = User.objects.get(username='demo.admin')
        teacher = User.objects.get(username='demo.teacher')
        self.assertEqual(administrator.role, User.Role.ORG_ADMIN)
        self.assertEqual(teacher.role, User.Role.TEACHER)
        self.assertTrue(administrator.check_password('DemoPassword!19'))
        self.assertIn('Demo data is ready', output.getvalue())
