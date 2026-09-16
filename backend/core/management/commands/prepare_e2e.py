from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    Camera,
    Classroom,
    ClassroomSession,
    Organization,
    Presentation,
    Report,
    Subject,
    User,
)


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
        subject = Subject.objects.create(
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

        User.objects.bulk_create([
            User(
                username=f'e2e.scale.teacher.{number:03d}',
                email=f'e2e.scale.teacher.{number:03d}@example.test',
                first_name='Scale',
                last_name=f'Teacher {number:03d}',
                role=User.Role.TEACHER,
                organization=organization,
                status=User.Status.ACTIVE,
            )
            for number in range(1, 22)
        ])
        scale_classrooms = Classroom.objects.bulk_create([
            Classroom(
                organization=organization,
                room_code=f'E2E-SCALE-{number:03d}',
                building='Scale Test Wing',
                capacity=30,
            )
            for number in range(1, 22)
        ])
        Camera.objects.bulk_create([
            Camera(
                classroom=scale_classroom,
                camera_name=f'E2E Scale Camera {number:03d}',
                position=Camera.Position.FRONT,
                status=Camera.Status.ACTIVE,
            )
            for number, scale_classroom in enumerate(scale_classrooms, start=1)
        ])
        Subject.objects.bulk_create([
            Subject(
                classroom=classroom,
                teacher=teacher,
                subject_code=f'E2E-SUBJECT-{number:03d}',
                subject_name=f'E2E Scale Subject {number:03d}',
            )
            for number in range(1, 22)
        ])
        presentations = Presentation.objects.bulk_create([
            Presentation(
                user=teacher,
                title=f'E2E Scale Presentation {number:03d}',
                file_name=f'scale-{number:03d}.pdf',
                processing_status=Presentation.ProcessingStatus.READY,
            )
            for number in range(1, 22)
        ])
        now = timezone.now()
        sessions = ClassroomSession.objects.bulk_create([
            ClassroomSession(
                user=teacher,
                subject=subject,
                presentation=presentation,
                session_date=timezone.localdate(now - timedelta(days=number)),
                started_at=now - timedelta(days=number),
                ended_at=now - timedelta(days=number) + timedelta(minutes=45),
            )
            for number, presentation in enumerate(presentations, start=1)
        ])
        Report.objects.bulk_create([
            Report(
                session=session,
                generated_by=teacher,
                report_type='pdf',
                report_path=f'reports/e2e-scale-{number:03d}.pdf',
            )
            for number, session in enumerate(sessions, start=1)
        ])

        self.stdout.write(self.style.SUCCESS('Synthetic E2E workspace is ready.'))
