import asyncio
import os
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection

from .presentation_processing import _find_libreoffice


def check_database():
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        return cursor.fetchone()[0] == 1


def check_storage():
    name = f'.health/{uuid4().hex}.txt'
    stored_name = None
    try:
        stored_name = default_storage.save(name, ContentFile(b'tagad-health-check'))
        return default_storage.exists(stored_name)
    finally:
        if stored_name:
            default_storage.delete(stored_name)


def check_presentation_converter():
    if _find_libreoffice():
        return True
    if os.name != 'nt':
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'PowerPoint.Application'):
            return True
    except (ImportError, FileNotFoundError, OSError):
        return False


async def _websocket_round_trip():
    layer = get_channel_layer()
    if layer is None:
        return False
    channel = await layer.new_channel('health.')
    message = {'type': 'health.check', 'nonce': uuid4().hex}
    await layer.send(channel, message)
    received = await asyncio.wait_for(layer.receive(channel), timeout=2)
    return received == message


def check_websocket():
    return async_to_sync(_websocket_round_trip)()


def run_readiness_checks(logger):
    checks = {
        'django': {'status': 'ok'},
    }
    dependencies = (
        ('postgresql', check_database),
        ('file_storage', check_storage),
        ('presentation_converter', check_presentation_converter),
        ('websocket', check_websocket),
    )
    for name, check in dependencies:
        try:
            ready = check() is True
        except Exception as error:
            ready = False
            logger.warning(
                'Operational dependency check failed.',
                extra={
                    'event': 'dependency_check_failed',
                    'component': name,
                    'exception_type': type(error).__name__,
                },
            )
        checks[name] = {'status': 'ok' if ready else 'failed'}
    return checks

