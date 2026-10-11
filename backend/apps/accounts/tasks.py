"""Background tasks for accounts.

Every task takes identifiers only and returns nothing. Email addresses, tokens and
message text are loaded or generated inside the task, so they never sit in the broker,
in task names or in worker logs.
"""

from __future__ import annotations

from smtplib import SMTPException

from celery import shared_task
from django.core.management import call_command

from .models import User

_EMAIL_RETRY = {
    "autoretry_for": (SMTPException, OSError),
    "retry_backoff": True,
    "retry_backoff_max": 600,
    "retry_jitter": True,
    "max_retries": 5,
}


def _active_user(user_id: str) -> User | None:
    return User.objects.filter(pk=user_id, is_active=True).first()


@shared_task(name="accounts.send_verification_email", **_EMAIL_RETRY)
def send_verification_email(user_id: str) -> None:
    from . import emails

    user = _active_user(user_id)
    if user is not None and user.email_verified_at is None:
        emails.send_verification(user)


@shared_task(name="accounts.send_password_reset_email", **_EMAIL_RETRY)
def send_password_reset_email(user_id: str) -> None:
    from . import emails

    user = _active_user(user_id)
    if user is not None:
        emails.send_password_reset(user)


@shared_task(name="accounts.send_account_exists_email", **_EMAIL_RETRY)
def send_account_exists_email(user_id: str) -> None:
    from . import emails

    user = _active_user(user_id)
    if user is not None:
        emails.send_account_exists(user)


@shared_task(name="accounts.erase_account")
def erase_account(user_id: str) -> None:
    from . import services

    services.erase_account(user_id)


@shared_task(name="accounts.purge_stale_accounts")
def purge_stale_accounts() -> None:
    from . import services

    services.purge_stale_accounts()


@shared_task(name="accounts.clear_expired_sessions")
def clear_expired_sessions() -> None:
    call_command("clearsessions")
