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
