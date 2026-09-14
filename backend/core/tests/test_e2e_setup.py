from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from core.management.commands.prepare_e2e import E2E_PASSWORD
from core.models import Camera, Classroom, Organization, Subject, User


class PrepareE2ECommandTests(TestCase):
    def test_command_refuses_to_touch_a_normal_database(self):
        with self.assertRaisesMessage(CommandError, 'tagad.e2e_settings'):
            call_command('prepare_e2e')

    @override_settings(E2E_TESTING=True)
    def test_command_creates_only_the_expected_synthetic_workspace(self):
        output = StringIO()

        call_command('prepare_e2e', stdout=output)

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Classroom.objects.count(), 1)
        self.assertEqual(Subject.objects.count(), 1)
        self.assertEqual(Camera.objects.count(), 1)
        system_admin = User.objects.get(username='e2e.system')
        teacher = User.objects.get(username='e2e.teacher')
        self.assertTrue(system_admin.is_superuser)
        self.assertEqual(teacher.role, User.Role.TEACHER)
        self.assertTrue(teacher.check_password(E2E_PASSWORD))
        self.assertIn('Synthetic E2E workspace is ready', output.getvalue())

