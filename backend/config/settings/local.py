"""Local development. Never use these settings on a public host."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", default="local-development-only-key-do-not-use-anywhere-else")
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "web"],  # noqa: S104
)

# The console email backend prints to stdout. Celery normally routes worker stdout
# through the logger, where the redaction filter (correctly) strips the address and the
# link token, which would make local sign-up impossible. Locally only, let it print raw.
CELERY_WORKER_REDIRECT_STDOUTS = False
