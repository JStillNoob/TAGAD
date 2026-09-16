import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.database_recovery import (
    DatabaseRecoveryError,
    create_database_backup,
    rehearse_database_recovery,
)


class Command(BaseCommand):
    help = 'Back up PostgreSQL, restore into a disposable database, verify it, and remove it.'

    def handle(self, *args, **options):
        self.stdout.write('Creating temporary backup and isolated restore database...')
        try:
            with tempfile.TemporaryDirectory(prefix='tagad-recovery-') as directory:
                backup = create_database_backup(Path(directory) / 'rehearsal.dump')
                rehearse_database_recovery(backup)
        except DatabaseRecoveryError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(
            'Database recovery rehearsal passed; the temporary database was removed.',
        ))

