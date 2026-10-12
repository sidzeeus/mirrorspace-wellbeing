from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class NoStoreApiMiddleware:
    """Tell browsers and proxies never to keep a copy of an API response.

    API responses hold personal data. `Cache-Control: no-store` stops them being
    written to a browser's disk cache or a shared proxy, whatever the client does.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.path.startswith("/api/") and "Cache-Control" not in response:
            response["Cache-Control"] = "no-store"
        return response
