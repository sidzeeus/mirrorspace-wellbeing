"""Signed, expiring tokens for the links sent by email. Nothing is stored server-side."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import User

_VERIFY_SALT = "accounts.email-verification"


def make_email_verification_token(user: User) -> str:
    return signing.dumps({"u": str(user.pk)}, salt=_VERIFY_SALT)


def read_email_verification_token(token: str) -> str | None:
    """Return the user id the token was issued for, or None if invalid or expired."""
    try:
        payload = signing.loads(
            token, salt=_VERIFY_SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE
        )
    except signing.BadSignature:
        return None
    user_id = payload.get("u") if isinstance(payload, dict) else None
    return user_id if isinstance(user_id, str) else None


def make_password_reset_parts(user: User) -> tuple[str, str]:
    """Return (uid, token). The token stops working once the password changes."""
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def user_from_password_reset_parts(uid: str, token: str) -> User | None:
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValidationError, ValueError, TypeError, OverflowError):
        return None
    return user if default_token_generator.check_token(user, token) else None
