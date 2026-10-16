import smtplib
from io import StringIO

import pytest
from django.core import mail
from django.core.management import CommandError, call_command


def test_sends_one_plain_email():
    out = StringIO()
    call_command("send_test_email", "owner@example.com", stdout=out)
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["owner@example.com"]
    assert "test email" in mail.outbox[0].subject
    assert "Accepted by" in out.getvalue()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (smtplib.SMTPAuthenticationError(535, b"bad owner@example.com"), "username or password"),
        (smtplib.SMTPDataError(550, b"rejected owner@example.com"), "code 550"),
        (ConnectionRefusedError("owner@example.com"), "Could not reach"),
    ],
)
def test_failures_explain_the_cause_without_quoting_the_server(monkeypatch, error, expected):
    def fail(self, fail_silently=False):
        raise error

    monkeypatch.setattr("django.core.mail.EmailMessage.send", fail)
    with pytest.raises(CommandError) as raised:
        call_command("send_test_email", "owner@example.com")
    assert expected in str(raised.value)
    assert "owner@example.com" not in str(raised.value)
