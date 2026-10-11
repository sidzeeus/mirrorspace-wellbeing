from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.crypto import salted_hmac
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

from config.api import IPThrottle

from .models import normalize_email

if TYPE_CHECKING:
    from rest_framework.views import APIView


class LoginIPThrottle(IPThrottle):
    scope = "login"


class LoginEmailThrottle(SimpleRateThrottle):
    """Limits attempts against one account, whichever address they come from.

    The cache key is a keyed hash of the email, so the address itself is never stored
    in Redis.
    """

    scope = "login_email"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        email = request.data.get("email") if isinstance(request.data, dict) else None
        if not isinstance(email, str) or not email.strip():
            return None
        digest = salted_hmac("accounts.login-throttle", normalize_email(email)).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class RegisterThrottle(IPThrottle):
    scope = "register"


class EmailActionThrottle(IPThrottle):
    """Endpoints that cause an email to be sent."""

    scope = "email_action"


class AccountDeleteThrottle(IPThrottle):
    scope = "account_delete"
