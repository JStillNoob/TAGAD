from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.models import Camera, Classroom, Organization, Subject, User


class Command(BaseCommand):
    help = 'Create or refresh a small, non-destructive TAGAD demo workspace.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            required=True,
            help='Password assigned to the demo administrator and teacher.',
        )

    def handle(self, *args, **options):
        try:
            validate_password(options['password'])
        except ValidationError as error:
            raise CommandError(' '.join(error.messages)) from error

        organization, _ = Organization.objects.update_or_create(
            organization_code='TAGAD-DEMO',
            defaults={
                'organization_name': 'TAGAD Demo School',
                'address': 'Demo Campus',
                'contact_email': 'demo@example.com',
                'status': Organization.Status.ACTIVE,
            },
        )

        self._user(
            'demo.admin', 'demo.admin@example.com', 'Demo', 'Administrator',
            User.Role.ORG_ADMIN, organization, options['password'],
        )
        teacher = self._user(
            'demo.teacher', 'demo.teacher@example.com', 'Demo', 'Teacher',
            User.Role.TEACHER, organization, options['password'],
        )

        classroom, _ = Classroom.objects.update_or_create(
            room_code='DEMO-101',
            defaults={'organization': organization, 'building': 'Demo Building', 'capacity': 35},
        )
        Subject.objects.update_or_create(
            subject_code='DEMO-IT101',
            defaults={
                'subject_name': 'Introduction to Computing',
                'classroom': classroom,
                'teacher': teacher,
            },
        )
        Camera.objects.update_or_create(
            classroom=classroom,
            position=Camera.Position.FRONT,
            defaults={'camera_name': 'Demo Front Camera', 'status': Camera.Status.ACTIVE},
        )

        self.stdout.write(self.style.SUCCESS(
            'Demo data is ready. Sign in as demo.admin or demo.teacher with the supplied password.',
        ))

    @staticmethod
    def _user(username, email, first_name, last_name, role, organization, password):
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'organization': organization,
                'status': User.Status.ACTIVE,
                'is_active': True,
            },
        )
        user.set_password(password)
        user.save(update_fields=['password'])
        return user
