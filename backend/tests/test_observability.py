"""Proves sensitive text stays out of logs and error reports (non-negotiable 6)."""

from __future__ import annotations

import io
import json
import logging

import pytest
from django.core import mail

from config.observability import (
    REDACTED,
    JsonFormatter,
    RedactionFilter,
    drop_breadcrumb,
    init_sentry,
    redact_text,
    scrub_sentry_event,
)
from tests.factories import DEFAULT_PASSWORD, UserFactory

CANARY_EMAIL = "canary.student@example.test"
CANARY_TEXT = "CANARY-7f3a-private-words"


@pytest.fixture
def log_output():
    """A logger wired exactly like production: redaction filter + JSON formatter."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactionFilter())
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("canary-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, stream


class TestRedactText:
    def test_removes_email_addresses(self):
        assert CANARY_EMAIL not in redact_text(f"sent to {CANARY_EMAIL} ok")

    @pytest.mark.parametrize(
        "text",
        [
            "password=hunter2secret",
            "token: abc.def.ghi",
            'Authorization="Bearer xyz123"',
            "sessionid=abcdef123456; path=/",
        ],
    )
    def test_removes_credential_values(self, text):
        cleaned = redact_text(text)
        assert REDACTED in cleaned
        for secret in ("hunter2secret", "abc.def.ghi", "xyz123", "abcdef123456"):
            assert secret not in cleaned

    def test_leaves_ordinary_text_alone(self):
        assert redact_text("account_erased user_id=42") == "account_erased user_id=42"


class TestLogPipeline:
    def test_output_is_one_json_object_per_line(self, log_output):
        logger, stream = log_output
        logger.info("something_happened", extra={"user_id": "abc", "count": 3})
        record = json.loads(stream.getvalue())
        assert record["message"] == "something_happened"
        assert record["user_id"] == "abc"
        assert record["count"] == 3
        assert record["level"] == "INFO"

    def test_email_in_message_and_args_is_removed(self, log_output):
        logger, stream = log_output
        logger.info("login for %s from %s", CANARY_EMAIL, "10.0.0.1")
        assert CANARY_EMAIL not in stream.getvalue()

    def test_sensitive_extra_keys_are_dropped_whatever_they_hold(self, log_output):
        logger, stream = log_output
        logger.info(
            "event",
            extra={
                "note": CANARY_TEXT,
                "prompt": CANARY_TEXT,
                "message_body": CANARY_TEXT,
                "display_name": CANARY_TEXT,
                "payload": {"text": CANARY_TEXT, "nested": {"password": CANARY_TEXT}},
                "recipients": [CANARY_EMAIL],
            },
        )
        output = stream.getvalue()
        assert CANARY_TEXT not in output
        assert CANARY_EMAIL not in output

    def test_exception_text_is_scrubbed(self, log_output):
        logger, stream = log_output
        try:
            raise ValueError(f"Key (email)=({CANARY_EMAIL}) already exists")
        except ValueError:
            logger.exception("database_error")
        output = stream.getvalue()
        assert CANARY_EMAIL not in output
        assert "ValueError" in output

    def test_project_logging_config_uses_the_redaction_filter(self, settings):
        handler = settings.LOGGING["handlers"]["console"]
        assert "redact" in handler["filters"]
        assert handler["formatter"] == "json"


@pytest.mark.django_db
class TestAccountFlowsDoNotLogPersonalData:
    def test_register_login_reset_and_delete_log_no_email_or_password(self, api_client, caplog):
        caplog.set_level(logging.DEBUG)
        password = DEFAULT_PASSWORD

        api_client.post(
            "/api/v1/auth/register",
            {
                "email": CANARY_EMAIL,
                "password": password,
                "age_confirmed": True,
                "display_name": CANARY_TEXT,
            },
            format="json",
        )
        api_client.post(
            "/api/v1/auth/register",
            {"email": CANARY_EMAIL, "password": password, "age_confirmed": True},
            format="json",
        )
        api_client.post(
            "/api/v1/auth/login", {"email": CANARY_EMAIL, "password": "wrong"}, format="json"
        )
        api_client.post("/api/v1/auth/password-reset", {"email": CANARY_EMAIL}, format="json")
        user = UserFactory(email="second.canary@example.test")
        api_client.force_authenticate(user)
        api_client.delete("/api/v1/account", {"password": password}, format="json")

        assert mail.outbox, "the flows should have run far enough to send email"
        logged = "\n".join(
            f"{r.getMessage()} {json.dumps(r.__dict__, default=str)}" for r in caplog.records
        )
        for secret in (CANARY_EMAIL, "second.canary@example.test", password, CANARY_TEXT):
            assert secret not in logged

    def test_task_names_and_arguments_carry_ids_only(self):
        from config.celery import app

        names = [n for n in app.tasks if n.startswith("accounts.")]
        assert names, "account tasks should be registered"
        for name in names:
            assert "@" not in name
            assert name == name.lower()

    def test_user_repr_does_not_contain_the_email(self):
        user = UserFactory(email=CANARY_EMAIL)
        assert CANARY_EMAIL not in str(user)
        assert CANARY_EMAIL not in repr(user)
        assert CANARY_EMAIL not in str(user.profile)


class TestSentryScrubbing:
    def event(self):
        return {
            "message": f"failed for {CANARY_EMAIL}",
            "logentry": {
                "message": "failed for %s",
                "formatted": f"failed for {CANARY_EMAIL}",
                "params": [CANARY_EMAIL],
            },
            "user": {"id": "1", "email": CANARY_EMAIL, "ip_address": "10.0.0.1"},
            "extra": {"body": CANARY_TEXT},
            "breadcrumbs": {"values": [{"message": CANARY_TEXT}]},
            "request": {
                "method": "POST",
                "url": "https://api.example.test/api/v1/auth/login?next=/x",
                "data": {"email": CANARY_EMAIL, "password": CANARY_TEXT},
                "cookies": {"sessionid": CANARY_TEXT},
                "headers": {"Cookie": CANARY_TEXT, "Authorization": CANARY_TEXT},
                "query_string": f"q={CANARY_TEXT}",
                "env": {"REMOTE_ADDR": "10.0.0.1"},
            },
            "exception": {
                "values": [
                    {
                        "type": "IntegrityError",
                        "value": f"Key (email)=({CANARY_EMAIL}) already exists",
                        "stacktrace": {
                            "frames": [
                                {
                                    "function": "view",
                                    "vars": {"note": CANARY_TEXT},
                                    "pre_context": [CANARY_TEXT],
                                    "post_context": [CANARY_TEXT],
                                }
                            ]
                        },
                    }
                ]
            },
        }

    def test_removes_every_trace_of_user_content(self):
        scrubbed = scrub_sentry_event(self.event(), {})
        dumped = json.dumps(scrubbed)
        assert CANARY_EMAIL not in dumped
        assert CANARY_TEXT not in dumped
        assert "10.0.0.1" not in dumped

    def test_keeps_what_is_needed_to_debug(self):
        scrubbed = scrub_sentry_event(self.event(), {})
        assert scrubbed["request"] == {
            "method": "POST",
            "url": "https://api.example.test/api/v1/auth/login",
        }
        assert scrubbed["exception"]["values"][0]["type"] == "IntegrityError"
        assert scrubbed["exception"]["values"][0]["stacktrace"]["frames"][0]["function"] == "view"

    def test_breadcrumbs_are_dropped(self):
        assert drop_breadcrumb({"message": CANARY_TEXT}, {}) is None

    def test_sentry_stays_off_without_a_dsn(self):
        assert init_sentry("", "test") is False

    def test_sentry_is_initialised_with_pii_off(self, monkeypatch):
        captured = {}
        monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: captured.update(kwargs))

        assert init_sentry("https://public@sentry.example.test/1", "test") is True
        assert captured["send_default_pii"] is False
        assert captured["include_local_variables"] is False
        assert captured["max_request_body_size"] == "never"
        assert captured["before_send"] is scrub_sentry_event
        assert captured["before_breadcrumb"] is drop_breadcrumb
