"""Account emails.

Links carry their token in the URL fragment (after `#`). Browsers do not send the
fragment to any server, so tokens stay out of access logs and Referer headers.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from .models import User
from .tokens import make_email_verification_token, make_password_reset_parts


def _send(user: User, template: str, subject: str, context: dict[str, Any]) -> None:
    body = render_to_string(
        f"accounts/email/{template}.txt",
        {"app_name": settings.APP_NAME, "frontend_url": settings.FRONTEND_URL, **context},
    )
    EmailMessage(subject=subject, body=body, to=[user.email]).send()


def send_verification(user: User) -> None:
    token = make_email_verification_token(user)
    _send(
        user,
        "verify",
        f"Confirm your email for {settings.APP_NAME}",
        {
            "link": f"{settings.FRONTEND_URL}/verify-email#token={token}",
            "valid_days": settings.EMAIL_VERIFICATION_MAX_AGE // 86400,
        },
    )


def send_password_reset(user: User) -> None:
    uid, token = make_password_reset_parts(user)
    _send(
        user,
        "password_reset",
        f"Reset your {settings.APP_NAME} password",
        {
            "link": f"{settings.FRONTEND_URL}/reset-password#uid={uid}&token={token}",
            "valid_minutes": settings.PASSWORD_RESET_TIMEOUT // 60,
        },
    )


def send_account_exists(user: User) -> None:
    _send(
        user,
        "account_exists",
        f"You already have a {settings.APP_NAME} account",
        {
            "login_link": f"{settings.FRONTEND_URL}/login",
            "reset_link": f"{settings.FRONTEND_URL}/forgot-password",
        },
    )
