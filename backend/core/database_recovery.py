import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import psycopg2
from django.conf import settings
from psycopg2 import sql


class DatabaseRecoveryError(RuntimeError):
    pass


logger = logging.getLogger('tagad.database_recovery')
SAFE_REHEARSAL_DATABASE = re.compile(r'^tagad_restore_test_[a-f0-9]{12}$')


def _database_config():
    database = settings.DATABASES['default']
    if 'postgresql' not in database['ENGINE']:
        raise DatabaseRecoveryError('Database recovery rehearsal requires PostgreSQL.')
    return database


def find_postgres_tool(name):
    configured = str(getattr(settings, f'{name.upper()}_PATH', '')).strip()
    if configured and Path(configured).is_file():
        return Path(configured)

    discovered = shutil.which(name)
    if discovered:
        return Path(discovered)

    program_files = Path(os.environ.get('ProgramFiles', r'C:\Program Files'))
    candidates = list((program_files / 'PostgreSQL').glob(f'*/bin/{name}.exe'))
    if candidates:
        return max(candidates, key=lambda path: int(path.parts[-3]) if path.parts[-3].isdigit() else 0)
    raise DatabaseRecoveryError(
        f'{name} was not found. Configure {name.upper()}_PATH in backend/.env.',
    )


def _tool_environment(database):
    environment = os.environ.copy()
    environment['PGPASSWORD'] = str(database.get('PASSWORD', ''))
    return environment


def _connection_arguments(database, database_name=None):
    return [
        '--host', str(database.get('HOST') or 'localhost'),
        '--port', str(database.get('PORT') or '5432'),
        '--username', str(database.get('USER') or ''),
        '--dbname', str(database_name or database['NAME']),
    ]


def _run(tool, arguments, database):
    result = subprocess.run(
        [str(tool), *arguments],
        capture_output=True,
        text=True,
        timeout=getattr(settings, 'POSTGRES_TOOL_TIMEOUT_SECONDS', 300),
        env=_tool_environment(database),
        check=False,
    )
    if result.returncode != 0:
        logger.error(
            'PostgreSQL utility failed.',
            extra={
                'event': 'postgres_utility_failed',
                'component': tool.name,
                'status_code': result.returncode,
            },
        )
        raise DatabaseRecoveryError(
            f'{tool.name} failed with exit code {result.returncode}. '
            'Review backend/logs/tagad.log and verify PostgreSQL connectivity.',
        )


def create_database_backup(output_path):
    database = _database_config()
    output = Path(output_path).resolve()
    if output.exists():
        raise DatabaseRecoveryError('Refusing to overwrite an existing backup file.')
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(find_postgres_tool('pg_dump'), [
        '--format=custom',
        '--no-owner',
        '--no-privileges',
        '--file', str(output),
        *_connection_arguments(database),
    ], database)
    if not output.is_file() or output.stat().st_size == 0:
        raise DatabaseRecoveryError('PostgreSQL did not create a usable backup file.')
    return output


def _connect(database, database_name):
    return psycopg2.connect(
        dbname=database_name,
        user=database.get('USER') or '',
        password=database.get('PASSWORD') or '',
        host=database.get('HOST') or 'localhost',
        port=database.get('PORT') or '5432',
    )


def _create_rehearsal_database(database, name):
    connection = _connect(database, 'postgres')
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    finally:
        connection.close()


def _drop_rehearsal_database(database, name):
    if not SAFE_REHEARSAL_DATABASE.fullmatch(name):
        raise DatabaseRecoveryError('Refusing to delete a database outside the rehearsal namespace.')
    connection = _connect(database, 'postgres')
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
    finally:
        connection.close()


def _verify_restored_database(database, name):
    with _connect(database, name) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM django_migrations')
            return cursor.fetchone()[0] > 0


def rehearse_database_recovery(backup_path):
    database = _database_config()
    active_name = str(database['NAME'])
    rehearsal_name = f'tagad_restore_test_{uuid4().hex[:12]}'
    if rehearsal_name == active_name or not SAFE_REHEARSAL_DATABASE.fullmatch(rehearsal_name):
        raise DatabaseRecoveryError('Could not create a safe rehearsal database name.')

    created = False
    try:
        try:
            _create_rehearsal_database(database, rehearsal_name)
        except psycopg2.Error as error:
            raise DatabaseRecoveryError(
                'PostgreSQL refused the temporary restore database. Grant the configured '
                'role CREATEDB temporarily or use an authorized recovery role.',
            ) from error
        created = True
        _run(find_postgres_tool('pg_restore'), [
            '--exit-on-error',
            '--no-owner',
            '--no-privileges',
            *_connection_arguments(database, rehearsal_name),
            str(Path(backup_path).resolve()),
        ], database)
        if not _verify_restored_database(database, rehearsal_name):
            raise DatabaseRecoveryError('The restored database did not contain migration history.')
        return rehearsal_name
    finally:
        if created:
            try:
                _drop_rehearsal_database(database, rehearsal_name)
            except psycopg2.Error as error:
                raise DatabaseRecoveryError(
                    f'Could not remove temporary database {rehearsal_name}. '
                    'Ask a PostgreSQL administrator to remove it immediately.',
                ) from error
