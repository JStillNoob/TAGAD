from django.core.management.base import BaseCommand, CommandError

from core.model_integration import model_artifact_status


class Command(BaseCommand):
    help = 'Verify configured TAGAD model artifact paths without loading the models.'

    def handle(self, *args, **options):
        statuses = model_artifact_status()
        for status in statuses:
            marker = 'READY' if status.ready else 'MISSING'
            location = status.path or '(not configured)'
            self.stdout.write(f'[{marker}] {status.name}: {location} — {status.detail}')
        if not all(status.ready for status in statuses):
            raise CommandError('Model setup is incomplete.')
        self.stdout.write(self.style.SUCCESS('All model artifacts are ready.'))
