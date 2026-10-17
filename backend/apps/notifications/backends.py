"""Django email backends with a daily sending cap, for a public demo.

Set one of these as EMAIL_BACKEND:

  apps.notifications.backends.CappedSMTPBackend  plain SMTP (Gmail, Mailpit, any relay)
  apps.notifications.backends.BrevoBackend       Brevo's HTTPS API, for hosts that block
                                                 outbound SMTP (Render's free tier does)

Both stop sending once EMAIL_DAILY_LIMIT messages have gone out today (0 means no
limit), so a public demo cannot be used to send mail in bulk. Failures are raised as
smtplib exceptions with SMTP-style codes, so every caller handles both backends the
same way: 5xx is permanent, 4xx is worth retrying. Nothing here logs an address, a
subject or a body.
"""

from __future__ import annotations

import json
import smtplib
import urllib.error
import urllib.request
from collections.abc import Sequence
from email.utils import parseaddr
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.utils import timezone

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def take_daily_quota(count: int) -> None:
    """Count `count` messages against today's limit, or refuse with a retryable error."""
    limit = settings.EMAIL_DAILY_LIMIT
    if not limit or not count:
        return
    key = f"email-sent:{timezone.now():%Y-%m-%d}"
    cache.add(key, 0, timeout=60 * 60 * 25)
    if cache.incr(key, count) > limit:
        cache.decr(key, count)
        raise smtplib.SMTPResponseException(452, b"daily email limit reached")


class CappedSMTPBackend(SMTPBackend):
    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        take_daily_quota(len(email_messages))
        return super().send_messages(email_messages)


class BrevoBackend(BaseEmailBackend):
    """Sends plain-text email through Brevo's transactional API (https://brevo.com).

    BREVO_API_KEY is read from settings on the server. The sender in DEFAULT_FROM_EMAIL
    must be a sender verified in the Brevo dashboard.
    """

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
            except smtplib.SMTPException:
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent

    def _send(self, message: EmailMessage) -> None:
        if not settings.BREVO_API_KEY:
            raise smtplib.SMTPResponseException(451, b"email provider not configured")
        take_daily_quota(1)
        name, address = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
        sender: dict[str, str] = {"email": address}
        if name:
            sender["name"] = name
        payload: dict[str, Any] = {
            "sender": sender,
            "to": [{"email": recipient} for recipient in message.recipients()],
            "subject": message.subject,
            "textContent": message.body,
        }
        if message.extra_headers:
            payload["headers"] = dict(message.extra_headers)
        request = urllib.request.Request(  # noqa: S310 - a fixed https URL
            BREVO_URL,
            data=json.dumps(payload).encode(),
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.EMAIL_TIMEOUT):  # noqa: S310
                pass
        except urllib.error.HTTPError as error:
            # 400 means Brevo rejected this message (for example, an invalid address).
            # Anything else (bad key, rate limit, outage) may work later.
            code = 550 if error.code == 400 else 451
            raise smtplib.SMTPResponseException(code, b"email provider refused") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise smtplib.SMTPResponseException(451, b"email provider unreachable") from None
