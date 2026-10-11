"""OpenAPI description of how the API authenticates."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SessionAuthScheme(OpenApiAuthenticationExtension):
    target_class = "config.api.SessionAuth"
    name = "sessionCookie"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {"type": "apiKey", "in": "cookie", "name": settings.SESSION_COOKIE_NAME}
