"""Local development. Never use these settings on a public host."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", default="local-development-only-key-do-not-use-anywhere-else")
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "web"],  # noqa: S104
)
