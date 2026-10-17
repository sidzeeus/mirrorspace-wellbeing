"""Hardening checks (README Prompt 8): tasks, settings, query counts and scale."""

from __future__ import annotations

import inspect
import re
import time
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib import admin
from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications import services as delivery
from apps.notifications import tasks as notification_tasks
from apps.notifications.models import Notification
from apps.sharing.models import ConsentRecord
from tests.factories import (
    CheckInFactory,
    EpisodeFactory,
    ExerciseEventFactory,
    ExerciseFactory,
    TriggerFactory,
    TrustedContactFactory,
    UserFactory,
)
from tests.harness import client_for
from tests.test_platform import PRODUCTION_ENV, manage

PROJECT_TASK = re.compile(r"^(accounts|notifications|audit|chat)\.[a-z_]+$")
ALLOWED_TASK_ARGUMENTS = {"user_id", "notification_id"}


def project_tasks():
    from config.celery import app

    app.loader.import_default_modules()
    app.autodiscover_tasks(force=True)
    return {name: task for name, task in app.tasks.items() if not name.startswith("celery.")}


class TestBackgroundTasks:
    def test_task_names_are_generic_identifiers(self):
        tasks = project_tasks()
        assert len(tasks) >= 11
        for name in tasks:
            assert PROJECT_TASK.match(name), name

    def test_tasks_accept_identifiers_only(self):
        """Arguments are stored in the broker and can be logged: ids only, no content."""
        for name, task in project_tasks().items():
            parameters = set(inspect.signature(task.run).parameters)
            assert parameters <= ALLOWED_TASK_ARGUMENTS, f"{name} takes {parameters}"

    def test_tasks_return_nothing(self):
        for name, task in project_tasks().items():
            assert inspect.signature(task.run).return_annotation in (None, "None"), name
        assert settings.CELERY_TASK_IGNORE_RESULT is True

    def test_every_scheduled_job_is_a_registered_task(self):
        tasks = project_tasks()
        for entry in settings.CELERY_BEAT_SCHEDULE.values():
            assert entry["task"] in tasks, entry["task"]
            assert "args" not in entry and "kwargs" not in entry


class TestSecuritySettings:
    def test_production_settings_are_locked_down(self):
        code = (
            "from django.conf import settings as s;"
            "assert s.DEBUG is False;"
            "assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE;"
            "assert s.SESSION_COOKIE_HTTPONLY and s.CSRF_COOKIE_HTTPONLY;"
            "assert s.SESSION_COOKIE_SAMESITE == 'Lax';"
            "assert s.SECURE_SSL_REDIRECT and s.SECURE_HSTS_SECONDS > 0;"
            "assert s.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https');"
            "assert s.X_FRAME_OPTIONS == 'DENY' and s.SECURE_CONTENT_TYPE_NOSNIFF;"
            "assert s.ALLOWED_HOSTS == ['api.example.test'];"
            "assert s.CORS_ALLOWED_ORIGINS == ['https://app.example.test'];"
            "assert not getattr(s, 'CORS_ALLOW_ALL_ORIGINS', False);"
            "assert s.SHOW_UNREVIEWED_CONTENT is False;"
            "assert s.CHAT_PROVIDER.endswith('OpenAICompatibleProvider');"
            "assert 'Argon2' in s.PASSWORD_HASHERS[0];"
            "assert s.REST_FRAMEWORK['NUM_PROXIES'] >= 1;"
            "assert s.DATA_UPLOAD_MAX_MEMORY_SIZE <= 262144;"
            "print('ok')"
        )
        result = manage("shell", "-c", code, env=PRODUCTION_ENV)
        assert result.returncode == 0, result.stderr

    def test_the_render_hostname_is_allowed_when_render_sets_it(self):
        result = manage(
            "shell",
            "-c",
            "from django.conf import settings as s;"
            "assert s.ALLOWED_HOSTS == ['api.example.test', 'mirrorspace-api.onrender.com'];"
            "print('ok')",
            env={**PRODUCTION_ENV, "RENDER_EXTERNAL_HOSTNAME": "mirrorspace-api.onrender.com"},
        )
        assert result.returncode == 0, result.stderr

    def test_unreviewed_content_cannot_be_enabled_in_production(self):
        result = manage(
            "shell",
            "-c",
            "from django.conf import settings as s;"
            "assert s.SHOW_UNREVIEWED_CONTENT is False; print('ok')",
            env={**PRODUCTION_ENV, "SHOW_UNREVIEWED_CONTENT": "true"},
        )
        assert result.returncode == 0, result.stderr

    def test_no_secret_has_a_usable_default(self):
        base = (settings.BASE_DIR / "config" / "settings" / "base.py").read_text(encoding="utf-8")
        production = (settings.BASE_DIR / "config" / "settings" / "production.py").read_text(
            encoding="utf-8"
        )
        assert 'SECRET_KEY = env("DJANGO_SECRET_KEY", default="")' in base
        for required in (
            "DJANGO_SECRET_KEY",
            "FIELD_ENCRYPTION_KEYS",
            "PSEUDONYM_KEY",
            "DATABASE_URL",
        ):
            assert (
                f'env("{required}")' in production
                or f'env.list("{required}")' in production
                or (f'env.db("{required}")' in production)
            ), required
        # The AI key is read by the provider SDK from the environment, never by settings.
        assert 'env("ANTHROPIC_API_KEY' not in base + production

    def test_admin_exposes_no_student_records(self):
        registered = {model.__name__ for model in admin.site._registry}
        assert registered <= {
            "User",
            "Group",
            "Exercise",
            "Resource",
            "ContentDocument",
        }, registered
        user_admin = admin.site._registry[User]
        assert "password" not in (user_admin.fields or [])

    @pytest.mark.django_db
    def test_request_bodies_are_size_limited(self, api_client):
        huge = '{"email": "' + "a" * 300_000 + '"}'
        response = api_client.post("/api/v1/auth/login", data=huge, content_type="application/json")
        assert response.status_code in (400, 413)

    def test_throttle_rates_cover_every_sensitive_action(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        assert set(rates) >= {
            "anon",
            "user",
            "login",
            "login_email",
            "register",
            "email_action",
            "account_delete",
            "export",
            "contact_add",
            "sos",
            "public_token",
            "chat",
        }


@pytest.mark.django_db
class TestQueryCounts:
    """List endpoints must not run one query per row (which would also be slow)."""

    LIMIT = 14

    @pytest.fixture
    def busy_user(self):
        user = UserFactory(display_name="Asha")
        exercises = [ExerciseFactory() for _ in range(6)]
        for _ in range(30):
            CheckInFactory(user=user)
        triggers = [TriggerFactory(user=user) for _ in range(20)]
        for trigger in triggers:
            trigger.preferred_exercises.set(exercises[:3])
        for index in range(30):
            EpisodeFactory(user=user, trigger=triggers[index % 20], helped_exercise=exercises[0])
            ExerciseEventFactory(user=user, exercise=exercises[index % 6])
        now = timezone.now()
        for index in range(3):
            contact = TrustedContactFactory(user=user)
            consent = ConsentRecord.objects.create(
                user=user,
                contact=contact,
                purpose="weekly_summary",
                notice_version="v",
                granted_at=now,
                last_confirmed_at=now,
            )
            for week in range(8):
                Notification.objects.create(
                    user=user,
                    purpose="weekly_summary",
                    contact=contact,
                    consent=consent,
                    idempotency_key=f"q:{index}:{week}:{user.pk}",
                    scheduled_at=now,
                )
        return user

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/check-ins",
            "/api/v1/episodes",
            "/api/v1/triggers",
            "/api/v1/exercises",
            "/api/v1/exercise-events",
            "/api/v1/trusted-contacts",
            "/api/v1/sharing/consent",
            "/api/v1/notifications",
            "/api/v1/patterns?days=90",
        ],
    )
    def test_list_endpoint_uses_a_bounded_number_of_queries(
        self, busy_user, path, django_assert_max_num_queries
    ):
        client = client_for(busy_user)
        with django_assert_max_num_queries(self.LIMIT):
            response = client.get(path)
        assert response.status_code == 200

    def test_export_of_a_busy_account_stays_bounded(self, busy_user, django_assert_max_num_queries):
        client = client_for(busy_user)
        with django_assert_max_num_queries(40):
            assert client.get("/api/v1/export").status_code == 200


@pytest.mark.django_db
class TestWeeklyTaskAtScale:
    def test_two_hundred_due_notes_are_planned_once_each(self, monkeypatch):
        queued: list[str] = []
        monkeypatch.setattr(notification_tasks.deliver, "delay", lambda pk: queued.append(pk))
        now = timezone.now()
        for _ in range(200):
            user = UserFactory(display_name="A")
            ConsentRecord.objects.create(
                user=user,
                contact=TrustedContactFactory(user=user),
                purpose="weekly_summary",
                notice_version="v",
                granted_at=now,
                last_confirmed_at=now,
                send_weekday=0,
                send_hour=9,
                next_send_at=now - timedelta(minutes=1),
            )

        started = time.perf_counter()
        planned = delivery.enqueue_due_weekly()
        elapsed = time.perf_counter() - started

        assert planned == 200
        assert len(queued) == len(set(queued)) == 200
        assert Notification.objects.count() == 200
        assert delivery.enqueue_due_weekly() == 0
        assert not ConsentRecord.objects.filter(next_send_at__lte=now).exists()
        assert elapsed < 30, f"planning 200 notes took {elapsed:.1f}s"

    def test_sending_two_hundred_notes_sends_two_hundred_emails(self, monkeypatch):
        queued: list[str] = []
        monkeypatch.setattr(notification_tasks.deliver, "delay", lambda pk: queued.append(pk))
        now = timezone.now()
        for _ in range(200):
            user = UserFactory(display_name="A")
            ConsentRecord.objects.create(
                user=user,
                contact=TrustedContactFactory(user=user),
                purpose="weekly_summary",
                notice_version="v",
                granted_at=now,
                last_confirmed_at=now,
                next_send_at=now - timedelta(minutes=1),
            )
        delivery.enqueue_due_weekly()

        # Each task delivered twice, as an at-least-once queue may do.
        outcomes = [delivery.attempt(pk) for pk in queued + queued]

        assert outcomes.count(delivery.Outcome.SENT) == 200
        assert outcomes.count(delivery.Outcome.SKIPPED) == 200
        assert len(mail.outbox) == 200
        assert len({message.to[0] for message in mail.outbox}) == 200
