"""Test settings: fast, deterministic, and never talking to a real provider."""

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-key-not-a-secret"
ALLOWED_HOSTS = ["testserver", "localhost"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Tasks run inline so tests can assert on their effects without a broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

STORAGES = {
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
