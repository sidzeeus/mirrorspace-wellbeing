"""Settings shared by every environment.

Values come from environment variables (documented in .env.example). The defaults here
are safe for local development only; production.py re-reads the important ones without
defaults so a missing variable stops the process instead of silently using a dev value.
"""

from pathlib import Path

import environ
from celery.schedules import crontab

from config.observability import init_sentry

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

env = environ.Env()

APP_NAME = env("APP_NAME", default="Mirrorspace")
ENVIRONMENT = env("ENVIRONMENT", default="local")

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Where the Next.js app is served. Used for links in email and for CORS/CSRF.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database, cache, queue -------------------------------------------------------

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://wellbeing:wellbeing@localhost:5432/wellbeing"
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
# Fail fast when the database is unreachable instead of hanging a request or a probe.
if "postgresql" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 5
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "wb",
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_IGNORE_RESULT = True  # results are never stored, so nothing can leak there
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False  # keep our redacting JSON logger in workers
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"socket_connect_timeout": 3, "socket_timeout": 5}
CELERY_BEAT_SCHEDULE = {
    "accounts-purge-stale-accounts": {
        "task": "accounts.purge_stale_accounts",
        "schedule": crontab(minute="17"),
    },
    "accounts-clear-expired-sessions": {
        "task": "accounts.clear_expired_sessions",
        "schedule": crontab(hour="3", minute="41"),
    },
}

# --- Authentication and sessions --------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Idle timeout: the session lasts this long after the most recent request.
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE_SECONDS", default=60 * 60 * 24 * 7)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=False)
SESSION_COOKIE_DOMAIN = env("COOKIE_DOMAIN", default=None)

# The frontend gets its CSRF token from GET /api/v1/auth/csrf, so the cookie itself
# does not need to be readable by JavaScript.
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN
CSRF_TRUSTED_ORIGINS: list[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[FRONTEND_URL])
CSRF_FAILURE_VIEW = "config.api.csrf_failure"

CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[FRONTEND_URL])
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"

PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT_SECONDS", default=60 * 60)
EMAIL_VERIFICATION_MAX_AGE = env.int("EMAIL_VERIFICATION_MAX_AGE_SECONDS", default=60 * 60 * 24 * 3)
# Accounts that never verify their email are removed after this many days.
UNVERIFIED_ACCOUNT_TTL_DAYS = env.int("UNVERIFIED_ACCOUNT_TTL_DAYS", default=7)

# --- Internationalisation ---------------------------------------------------------

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("hi", "Hindi")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_USER_TIMEZONE = "Asia/Kolkata"

# --- Static files -----------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Request limits ---------------------------------------------------------------

DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024  # JSON bodies only; nothing here is large
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200

# --- Email ------------------------------------------------------------------------

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")

# --- Django REST Framework --------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["config.api.SessionAuth"],
    # Private by default. A public endpoint has to say so explicitly.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "240/min",
        "login": "5/min",
        "login_email": "10/hour",
        "register": "5/hour",
        "email_action": "5/hour",
        "account_delete": "5/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "config.api.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # How many trusted reverse proxies sit in front of the API. Used to read the real
    # client address for rate limiting without trusting a spoofed X-Forwarded-For.
    "NUM_PROXIES": env.int("NUM_PROXIES", default=0),
}

SPECTACULAR_SETTINGS = {
    "TITLE": f"{APP_NAME} API",
    "DESCRIPTION": (
        "Wellbeing support prototype for students aged 18 and over. "
        "Not therapy, diagnosis or emergency monitoring."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
}

ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# --- Logging and error tracking ---------------------------------------------------

LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "config.observability.RedactionFilter"}},
    "formatters": {"json": {"()": "config.observability.JsonFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["redact"],
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "celery": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

init_sentry(
    dsn=env("SENTRY_DSN", default=""),
    environment=ENVIRONMENT,
    release=env("RELEASE", default=None),
)
