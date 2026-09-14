"""Settings used only by the isolated Playwright browser suite."""

from .settings import *  # noqa: F403


E2E_TESTING = True
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

E2E_ROOT = BASE_DIR / '.e2e'  # noqa: F405
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': E2E_ROOT / 'test.sqlite3',
    },
}
MEDIA_ROOT = E2E_ROOT / 'media'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:4173']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
FRONTEND_URL = 'http://127.0.0.1:4173'
ENABLE_PIPELINE_SIMULATOR = True

