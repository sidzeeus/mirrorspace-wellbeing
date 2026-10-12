"""Every API route, enumerated (README Prompt 8, non-negotiable 7).

These tests walk the URL configuration, so a route added later is covered without
anyone remembering to write a test for it. For each route they assert:

- it requires sign-in, unless it is on the short, explicit list of public routes;
- a route that serves rows owned by a user is built on `OwnedModelViewSet`, and a
  cross-user contract test exists for it;
- writes are protected against cross-site request forgery;
- an unknown id answers 404, never a server error.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import uuid
from dataclasses import dataclass

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

import apps
from config.views import CsrfProtectedAPIView, OwnedModelViewSet
from tests.factories import UserFactory
from tests.harness import OwnedResourceContract, SingletonResourceContract, client_for

# Routes that answer without sign-in, and why each one has to.
PUBLIC_ROUTES = {
    "health": "liveness probe",
    "ready": "readiness probe",
    "schema": "API description (staff only in production)",
    "auth-csrf": "hands out the CSRF token needed to sign in",
    "auth-register": "creating an account",
    "auth-verify-email": "opened from an emailed link before signing in",
    "auth-resend-verification": "before the first sign-in",
    "auth-login": "signing in",
    "auth-password-reset": "forgotten password",
    "auth-password-reset-confirm": "opened from an emailed link",
    "resource-list": "helplines must be visible before sign-up and offline",
    "resource-detail": "helplines must be visible before sign-up and offline",
    "sharing-notices": "notice versions, shown during onboarding",
    "chat-info": "what the chat is and is not, shown before use",
    "invitation-view": "a trusted contact has no account; a signed token is their proof",
    "invitation-accept": "as above",
    "invitation-decline": "as above",
    "unsubscribe": "as above",
    "unsubscribe-one-click": "called by mail providers; a signed token is the credential",
    "webhook-email-events": "called by the email provider; a shared secret is the credential",
}

# Public writes that cannot carry a CSRF token because no browser of ours makes them.
CSRF_EXEMPT_BY_DESIGN = {"unsubscribe-one-click", "webhook-email-events"}

WRITE_METHODS = ("post", "put", "patch", "delete")
PARAMETER = re.compile(r"\(\?P<(\w+)>[^)]+\)")


@dataclass(frozen=True)
class Route:
    name: str
    pattern: str
    view_class: type
    methods: tuple[str, ...]

    @property
    def has_id(self) -> bool:
        return bool(PARAMETER.search(self.pattern))

    def url(self, value: str | None = None) -> str:
        path = PARAMETER.sub(value or str(uuid.uuid4()), self.pattern)
        return "/" + path.replace("^", "").replace("$", "").replace("\\", "")


def _walk(patterns, prefix=""):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry


def api_routes() -> list[Route]:
    routes = []
    for pattern, entry in _walk(get_resolver().url_patterns):
        if not pattern.startswith("api/v1/"):
            continue
        callback = entry.callback
        view_class = getattr(callback, "cls", None)
        assert view_class is not None, f"{pattern} is not a class-based API view"
        actions = getattr(callback, "actions", None)
        if actions:
            methods = tuple(actions)
        else:
            methods = tuple(m for m in ("get", *WRITE_METHODS) if hasattr(view_class, m))
        routes.append(Route(entry.name or "", pattern, view_class, methods))
    return routes


ROUTES = api_routes()
PROTECTED = [route for route in ROUTES if route.name not in PUBLIC_ROUTES]
OWNED = [route for route in ROUTES if issubclass(route.view_class, OwnedModelViewSet)]


def _ids(routes):
    return [f"{route.name}" for route in routes]


def test_there_are_routes_and_every_one_is_named():
    assert len(ROUTES) >= 50
    assert all(route.name for route in ROUTES)
    assert all(route.methods for route in ROUTES)


def test_public_list_is_exact():
    """Nothing is public by accident, and the list has no stale entries."""
    names = {route.name for route in ROUTES}
    assert set(PUBLIC_ROUTES) <= names, set(PUBLIC_ROUTES) - names
    declared_public = {
        route.name
        for route in ROUTES
        if AllowAny in getattr(route.view_class, "permission_classes", [])
    }
    # "schema" is drf-spectacular's own view; its permission comes from settings.
    assert declared_public | {"schema"} == set(PUBLIC_ROUTES)


@pytest.mark.django_db
@pytest.mark.parametrize("route", PROTECTED, ids=_ids(PROTECTED))
def test_protected_route_requires_sign_in(route):
    for method in route.methods:
        response = getattr(APIClient(), method)(route.url(), {}, format="json")
        assert response.status_code == 401, (
            f"{method.upper()} {route.url()} answered {response.status_code}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize("route", PROTECTED, ids=_ids(PROTECTED))
def test_protected_writes_need_a_csrf_token(route):
    user = UserFactory()
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    for method in route.methods:
        if method not in WRITE_METHODS:
            continue
        response = getattr(client, method)(route.url(), {}, format="json")
        assert response.status_code == 403, (
            f"{method.upper()} {route.url()} accepted a forged request"
        )


@pytest.mark.django_db
def test_public_writes_need_a_csrf_token_too():
    for route in ROUTES:
        if route.name not in PUBLIC_ROUTES or route.name in CSRF_EXEMPT_BY_DESIGN:
            continue
        if "post" not in route.methods:
            continue
        assert issubclass(route.view_class, CsrfProtectedAPIView), route.name
        response = APIClient(enforce_csrf_checks=True).post(route.url(), {}, format="json")
        assert response.status_code == 403, route.name


def test_every_user_owned_model_is_served_only_through_the_owned_base():
    """A viewset over a model with a `user` field must use the scoping base class."""
    for route in ROUTES:
        model = getattr(route.view_class, "model", None)
        if model is None:
            queryset = getattr(route.view_class, "queryset", None)
            model = getattr(queryset, "model", None)
        if model is None:
            continue
        if any(field.name == "user" for field in model._meta.get_fields()):
            assert issubclass(route.view_class, OwnedModelViewSet), (
                f"{route.name} serves {model.__name__} without the ownership base class"
            )


def _contract_urls() -> set[str]:
    """Import every test module and collect the URLs the cross-user contracts cover."""
    for package in pkgutil.iter_modules(apps.__path__, "apps."):
        tests = f"{package.name}.tests"
        try:
            module = importlib.import_module(tests)
        except ModuleNotFoundError:
            continue
        for found in pkgutil.iter_modules(module.__path__, f"{tests}."):
            importlib.import_module(found.name)
    importlib.import_module("tests.test_data_coverage")

    def subclasses(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from subclasses(sub)

    urls = {c.list_url for c in subclasses(OwnedResourceContract) if c.list_url}
    urls |= {c.url for c in subclasses(SingletonResourceContract) if getattr(c, "url", None)}
    return urls


def test_every_owned_route_has_a_cross_user_contract_test():
    covered = _contract_urls()
    owned_collections = {route.url() for route in OWNED if not route.has_id}
    assert owned_collections, "expected owned collections"
    missing = sorted(owned_collections - covered)
    assert missing == [], f"no cross-user contract test for: {missing}"
    assert "/api/v1/safety-plan" in covered


def test_session_scoped_routes_take_no_id():
    """Signed-in routes that are not owned collections act on the session's user only,
    so their URLs must carry no identifier that could be swapped for someone else's."""
    for route in PROTECTED:
        if issubclass(route.view_class, OwnedModelViewSet):
            continue
        if route.view_class.__name__ == "ExerciseViewSet":
            continue  # shared content, not personal
        assert not route.has_id, f"{route.name} takes an id but is not ownership-scoped"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route", [r for r in OWNED if r.has_id], ids=_ids([r for r in OWNED if r.has_id])
)
def test_unknown_or_malformed_ids_are_not_found(route):
    client = client_for(UserFactory())
    for value in (str(uuid.uuid4()), "not-a-uuid", "1", "..%2F..%2Fetc"):
        for method in route.methods:
            response = getattr(client, method)(route.url(value), {}, format="json")
            assert response.status_code in (404, 405), (
                f"{method.upper()} {route.url(value)} answered {response.status_code}"
            )


@pytest.mark.django_db
def test_api_responses_are_never_cached(api_client):
    public = api_client.get("/api/v1/resources")
    private = client_for(UserFactory()).get("/api/v1/check-ins")
    assert public.headers["Cache-Control"] == "no-store"
    assert private.headers["Cache-Control"] == "no-store"
