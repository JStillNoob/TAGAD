from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import Camera, Classroom, Organization, Subject, User


E2E_PASSWORD = 'BrowserTest!2026'


class Command(BaseCommand):
    help = 'Create deterministic synthetic records for the isolated browser suite.'

    def handle(self, *args, **options):
        if not getattr(settings, 'E2E_TESTING', False):
            raise CommandError('prepare_e2e can only run with tagad.e2e_settings.')

        organization = Organization.objects.create(
            organization_name='E2E Test School',
            organization_code='E2E-SCHOOL',
            address='Synthetic Test Campus',
            contact_email='e2e-school@example.test',
            status=Organization.Status.ACTIVE,
        )

        User.objects.create_user(
            username='e2e.system',
            email='e2e.system@example.test',
            first_name='E2E',
            last_name='System Admin',
            password=E2E_PASSWORD,
            role=User.Role.SYSTEM_ADMIN,
            status=User.Status.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )
        User.objects.create_user(
            username='e2e.admin',
            email='e2e.admin@example.test',
            first_name='E2E',
            last_name='Organization Admin',
            password=E2E_PASSWORD,
            role=User.Role.ORG_ADMIN,
            organization=organization,
            status=User.Status.ACTIVE,
        )
        teacher = User.objects.create_user(
            username='e2e.teacher',
            email='e2e.teacher@example.test',
            first_name='E2E',
            last_name='Teacher',
            password=E2E_PASSWORD,
            role=User.Role.TEACHER,
            organization=organization,
            status=User.Status.ACTIVE,
        )

        classroom = Classroom.objects.create(
            organization=organization,
            room_code='E2E-101',
            building='Test Building',
            capacity=30,
        )
        Subject.objects.create(
            classroom=classroom,
            teacher=teacher,
            subject_code='E2E-IT101',
            subject_name='Browser Testing Basics',
        )
        Camera.objects.create(
            classroom=classroom,
            camera_name='E2E Front Camera',
            position=Camera.Position.FRONT,
            status=Camera.Status.ACTIVE,
        )

        self.stdout.write(self.style.SUCCESS('Synthetic E2E workspace is ready.'))

