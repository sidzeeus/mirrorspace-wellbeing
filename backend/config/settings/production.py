"""Production settings.

Everything security-relevant is read without a default: a missing variable stops the
process at start-up rather than falling back to a development value.
"""

from .base import *  # noqa: F403
from .base import DATABASES, REST_FRAMEWORK, SPECTACULAR_SETTINGS, env

DEBUG = False
ENVIRONMENT = env("ENVIRONMENT", default="production")

SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
FRONTEND_URL = env("FRONTEND_URL").rstrip("/")

DATABASES["default"].update(env.db("DATABASE_URL"))
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
if "postgresql" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 5

REDIS_URL = env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "wb",
    }
}
CELERY_BROKER_URL = REDIS_URL

# --- HTTPS ------------------------------------------------------------------------

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# Health probes come from inside the platform over plain HTTP.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$", r"^api/v1/ready$"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Start low, raise to a year once HTTPS is confirmed working on every hostname.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
# Preloading is hard to undo, so it stays an explicit opt-in (security.W021).
SILENCED_SYSTEM_CHECKS = ["security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_DOMAIN = env("COOKIE_DOMAIN", default="") or None
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# --- Email ------------------------------------------------------------------------

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# --- API --------------------------------------------------------------------------

REST_FRAMEWORK["NUM_PROXIES"] = env.int("NUM_PROXIES", default=1)
# The API description is for the team, not the public.
SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = ["rest_framework.permissions.IsAdminUser"]

STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
