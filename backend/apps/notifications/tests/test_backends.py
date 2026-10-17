"""The capped SMTP backend and the Brevo HTTPS backend."""

from __future__ import annotations

import io
import json
import logging
import smtplib
import urllib.error

import pytest
from django.core.cache import cache
from django.core.mail import EmailMessage, get_connection

from apps.notifications import providers

CANARY = "canary-body-7f3a"
CANARY_EMAIL = "canary-7f3a@example.test"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def brevo(settings, monkeypatch):
    settings.EMAIL_BACKEND = "apps.notifications.backends.BrevoBackend"
    settings.BREVO_API_KEY = "test-key-not-real"
    settings.DEFAULT_FROM_EMAIL = "Mirrorspace <sender@example.test>"
    sent: list[dict] = []
    state: dict = {"error": None}

    def fake_urlopen(request, timeout):
        if state["error"] is not None:
            raise state["error"]
        sent.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data),
            }
        )
        return FakeResponse(b'{"messageId": "<abc@brevo>"}')

    monkeypatch.setattr("apps.notifications.backends.urllib.request.urlopen", fake_urlopen)
    return sent, state


def send(**headers):
    return providers.send_email(to=CANARY_EMAIL, subject="Hello", body=CANARY, headers=headers)


class TestBrevoBackend:
    def test_sends_plain_text_over_https_with_the_key_in_a_header(self, brevo):
        sent, _ = brevo
        send(**{"List-Unsubscribe": "<https://example.test/u>"})
        [request] = sent
        assert request["url"] == "https://api.brevo.com/v3/smtp/email"
        assert request["headers"]["Api-key"] == "test-key-not-real"
        body = request["body"]
        assert body["sender"] == {"email": "sender@example.test", "name": "Mirrorspace"}
        assert body["to"] == [{"email": CANARY_EMAIL}]
        assert body["textContent"] == CANARY
        assert body["headers"]["List-Unsubscribe"] == "<https://example.test/u>"

    def test_a_rejected_message_is_permanent(self, brevo):
        _, state = brevo
        state["error"] = urllib.error.HTTPError("u", 400, "bad", {}, None)
        with pytest.raises(providers.PermanentSendError):
            send()

    @pytest.mark.parametrize(
        "error",
        [
            urllib.error.HTTPError("u", 401, "unauthorised", {}, None),
            urllib.error.HTTPError("u", 429, "slow down", {}, None),
            urllib.error.HTTPError("u", 503, "down", {}, None),
            urllib.error.URLError("refused"),
            TimeoutError(),
        ],
    )
    def test_other_failures_are_retryable_and_log_nothing_sensitive(self, brevo, caplog, error):
        caplog.set_level(logging.DEBUG)
        _, state = brevo
        state["error"] = error
        with pytest.raises(providers.TransientSendError):
            send()
        assert CANARY not in caplog.text
        assert CANARY_EMAIL not in caplog.text

    def test_without_a_key_nothing_is_sent(self, brevo, settings):
        sent, _ = brevo
        settings.BREVO_API_KEY = ""
        with pytest.raises(providers.TransientSendError):
            send()
        assert sent == []

    def test_account_emails_go_through_it_too(self, brevo):
        sent, _ = brevo
        EmailMessage(subject="s", body="b", to=[CANARY_EMAIL]).send()
        assert len(sent) == 1


class TestDailyLimit:
    def test_brevo_stops_at_the_limit_and_the_send_can_be_retried(self, brevo, settings):
        sent, _ = brevo
        settings.EMAIL_DAILY_LIMIT = 2
        send()
        send()
        with pytest.raises(providers.TransientSendError):
            send()
        assert len(sent) == 2

    def test_smtp_stops_at_the_limit(self, settings):
        settings.EMAIL_DAILY_LIMIT = 1
        connection = get_connection("apps.notifications.backends.CappedSMTPBackend")
        connection.open = lambda: False  # no real SMTP server in tests

        sent: list[int] = []

        def fake_send(self, email_messages):
            sent.append(len(email_messages))
            return len(email_messages)

        base = "django.core.mail.backends.smtp.EmailBackend.send_messages"
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(base, fake_send)
            connection.send_messages([EmailMessage(subject="s", body="b", to=["a@example.test"])])
            with pytest.raises(smtplib.SMTPResponseException) as refused:
                connection.send_messages(
                    [EmailMessage(subject="s", body="b", to=["a@example.test"])]
                )
        assert refused.value.smtp_code == 452
        assert sent == [1]

    def test_zero_means_no_limit(self, brevo, settings):
        sent, _ = brevo
        settings.EMAIL_DAILY_LIMIT = 0
        for _ in range(5):
            send()
        assert len(sent) == 5
