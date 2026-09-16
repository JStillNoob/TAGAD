from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import psycopg2
from django.test import SimpleTestCase

from core.database_recovery import (
    DatabaseRecoveryError,
    create_database_backup,
    rehearse_database_recovery,
)


POSTGRES_DATABASE = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'tagad_active',
    'USER': 'tagad_user',
    'PASSWORD': 'private-password',
    'HOST': 'database.internal',
    'PORT': '5432',
}


class DatabaseRecoveryTests(SimpleTestCase):
    @patch('core.database_recovery.find_postgres_tool', return_value=Path('pg_dump'))
    @patch('core.database_recovery.subprocess.run')
    def test_backup_passes_password_only_through_environment(self, run, _find_tool):
        run.return_value = Mock(returncode=0)
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'backup.dump'

            def create_output(command, **kwargs):
                output.write_bytes(b'valid-backup')
                return Mock(returncode=0)

            run.side_effect = create_output
            with patch('core.database_recovery._database_config', return_value=POSTGRES_DATABASE):
                create_database_backup(output)

        command = run.call_args.args[0]
        environment = run.call_args.kwargs['env']
        self.assertNotIn('private-password', command)
        self.assertEqual(environment['PGPASSWORD'], 'private-password')

    @patch('core.database_recovery._drop_rehearsal_database')
    @patch('core.database_recovery._create_rehearsal_database')
    @patch('core.database_recovery.find_postgres_tool', return_value=Path('pg_restore'))
    @patch('core.database_recovery._run', side_effect=DatabaseRecoveryError('restore failed'))
    def test_failed_restore_still_removes_only_rehearsal_database(
        self, _run, _find_tool, create_database, drop_database,
    ):
        create_database.return_value = None

        with patch('core.database_recovery._database_config', return_value=POSTGRES_DATABASE):
            with self.assertRaises(DatabaseRecoveryError):
                rehearse_database_recovery('backup.dump')

        rehearsal_name = create_database.call_args.args[1]
        self.assertRegex(rehearsal_name, r'^tagad_restore_test_[a-f0-9]{12}$')
        self.assertNotEqual(rehearsal_name, POSTGRES_DATABASE['NAME'])
        drop_database.assert_called_once_with(POSTGRES_DATABASE, rehearsal_name)

    @patch('core.database_recovery._drop_rehearsal_database')
    @patch(
        'core.database_recovery._create_rehearsal_database',
        side_effect=psycopg2.Error('permission details'),
    )
    def test_permission_failure_is_safe_and_does_not_attempt_deletion(
        self, _create_database, drop_database,
    ):
        with patch('core.database_recovery._database_config', return_value=POSTGRES_DATABASE):
            with self.assertRaisesRegex(DatabaseRecoveryError, 'CREATEDB'):
                rehearse_database_recovery('backup.dump')

        drop_database.assert_not_called()
