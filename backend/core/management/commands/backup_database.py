from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.database_recovery import DatabaseRecoveryError, create_database_backup


class Command(BaseCommand):
    help = 'Create a PostgreSQL custom-format backup without exposing credentials.'

    def add_arguments(self, parser):
        parser.add_argument('--output', help='Output path; must be inside DATABASE_BACKUP_ROOT.')

    def handle(self, *args, **options):
        backup_root = settings.DATABASE_BACKUP_ROOT.resolve()
        requested = options['output']
        output = (
            backup_root / f'tagad-{datetime.now().strftime("%Y%m%d-%H%M%S")}.dump'
            if not requested else settings.BASE_DIR / requested
        ).resolve()
        if backup_root not in output.parents:
            raise CommandError('Backup output must be inside DATABASE_BACKUP_ROOT.')
        try:
            created = create_database_backup(output)
        except DatabaseRecoveryError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f'Backup created: {created}'))

