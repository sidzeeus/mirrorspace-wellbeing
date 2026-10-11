from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from tests.factories import DEFAULT_PASSWORD, UserFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    """Throttle counters live in the cache; start every test from zero."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _run_on_commit_immediately(monkeypatch):
    """Tests run inside a transaction that never commits, so run hooks straight away."""
    monkeypatch.setattr(
        "django.db.transaction.on_commit", lambda func, using=None, robust=False: func()
    )


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user) -> APIClient:
    client = APIClient()
    assert client.login(email=user.email, password=DEFAULT_PASSWORD)
    return client


@pytest.fixture
def set_now(monkeypatch):
    """Freeze "now". Use force-authenticated clients afterwards (sessions have expiry)."""

    def _set(moment):
        monkeypatch.setattr("django.utils.timezone.now", lambda: moment)

    return _set


@pytest.fixture
def as_user():
    """An API client acting as `user` without a session, safe to use with `set_now`."""

    def _client(user) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _client
