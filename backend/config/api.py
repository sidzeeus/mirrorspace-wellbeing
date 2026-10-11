"""Shared API building blocks: authentication, pagination, throttles and CSRF failure.

This module is named in REST_FRAMEWORK settings, so it must not import
`rest_framework.views` (that would be a circular import). View base classes live in
`config/views.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, JsonResponse
from rest_framework.authentication import SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

if TYPE_CHECKING:
    from rest_framework.views import APIView


class SessionAuth(SessionAuthentication):
    """Session authentication that answers 401 (not 403) when nobody is signed in."""

    def authenticate_header(self, request: Request) -> str:
        return "Session"


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IPThrottle(SimpleRateThrottle):
    """Rate limit by client address for a named scope, signed in or not."""

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def csrf_failure(request: HttpRequest, reason: str = "", **kwargs: Any) -> JsonResponse:
    return JsonResponse(
        {
            "detail": "Security check failed. Reload the page and try again.",
            "code": "csrf_failed",
        },
        status=403,
    )
