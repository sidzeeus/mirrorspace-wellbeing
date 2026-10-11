"""The single place that talks to the email provider.

Everything else calls `send_email` and handles two outcomes: a transient failure
(try again later) or a permanent one (this address will never work: stop). Swapping
providers means changing this file only.
"""

from __future__ import annotations

import smtplib
from email.utils import make_msgid

from django.core.mail import EmailMessage


class TransientSendError(Exception):
    """Worth retrying: the provider or the network had a temporary problem."""


class PermanentSendError(Exception):
    """A hard bounce: the address is invalid or refuses mail. Never retry."""


def _is_permanent(code: int) -> bool:
    return 500 <= code < 600


def send_email(*, to: str, subject: str, body: str, headers: dict[str, str]) -> str:
    """Send one plain-text email. Returns a reference that identifies the message."""
    message_id = make_msgid()
    message = EmailMessage(
        subject=subject, body=body, to=[to], headers={**headers, "Message-ID": message_id}
    )
    try:
        message.send(fail_silently=False)
    except smtplib.SMTPRecipientsRefused as exc:
        codes = [code for code, _ in exc.recipients.values()]
        if codes and all(_is_permanent(code) for code in codes):
            raise PermanentSendError from None
        raise TransientSendError from None
    except smtplib.SMTPResponseException as exc:
        # `from None` drops the original exception, whose text can quote the address.
        if _is_permanent(exc.smtp_code):
            raise PermanentSendError from None
        raise TransientSendError from None
    except (smtplib.SMTPException, OSError):
        raise TransientSendError from None
    return message_id
