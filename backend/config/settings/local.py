"""Local development. Never use these settings on a public host."""

import base64

from .base import *  # noqa: F403
from .base import env

DEBUG = True

# A fixed development key so encrypted fields work out of the box. Not a secret.
_DEV_FIELD_KEY = base64.urlsafe_b64encode(b"local-development-only-key-0000!").decode()
FIELD_ENCRYPTION_KEYS = env.list("FIELD_ENCRYPTION_KEYS", default=[_DEV_FIELD_KEY])
PSEUDONYM_KEY = env("PSEUDONYM_KEY", default="local-development-only-pseudonym-key")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="local-development-only-key-do-not-use-anywhere-else")
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "web"],  # noqa: S104
)

# The console email backend prints to stdout. Celery normally routes worker stdout
# through the logger, where the redaction filter (correctly) strips the address and the
# link token, which would make local sign-up impossible. Locally only, let it print raw.
CELERY_WORKER_REDIRECT_STDOUTS = False

# The development server starts a new thread per request. Persistent connections would
# pile up one per thread until PostgreSQL refuses new ones (seen as /ready answering 503
# under a burst), so they are off here. Production's worker processes reuse them safely.
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
