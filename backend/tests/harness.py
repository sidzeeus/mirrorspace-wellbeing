"""Reusable cross-user access tests (non-negotiable 7).

Every endpoint that serves user-owned rows gets a subclass of `OwnedResourceContract`.
The subclass says how to build an object and where it lives; the contract then proves
that one student can never list, read, change or delete another student's rows, and
that nobody can do any of it without signing in.

    @pytest.mark.django_db
    class TestCheckInIsolation(OwnedResourceContract):
        list_url = "/api/v1/check-ins"
        update_payload = {"mood": 3}

        def make(self, user):
            return CheckInFactory(user=user)

`tests/test_harness.py` checks that the contract really fails against a leaky endpoint.
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.db import models
from rest_framework.test import APIClient

from .factories import DEFAULT_PASSWORD, UserFactory


def client_for(user: Any) -> APIClient:
    client = APIClient()
    assert client.login(email=user.email, password=DEFAULT_PASSWORD)
    return client


class OwnedResourceContract:
    """Subclass once per user-owned collection endpoint."""

    #: Collection URL, for example "/api/v1/check-ins". None if there is no list route.
    list_url: ClassVar[str | None] = None
    #: Body used for PUT/PATCH attempts against another user's object.
    update_payload: ClassVar[dict[str, Any]] = {}
    #: Detail methods the endpoint supports. Unsupported ones must not be listed.
    detail_methods: ClassVar[tuple[str, ...]] = ("get", "put", "patch", "delete")
    #: Name of the identifier field in API responses.
    id_field: ClassVar[str] = "id"

    def make(self, user: Any) -> models.Model:
        """Create and return one object owned by `user`."""
        raise NotImplementedError

    def detail_url(self, obj: models.Model) -> str | None:
        return f"{self.list_url}/{obj.pk}" if self.list_url else None

    # --- helpers -----------------------------------------------------------------

    def _snapshot(self, obj: models.Model) -> dict[str, Any]:
        fresh = type(obj)._default_manager.get(pk=obj.pk)
        return {
            f.attname: getattr(fresh, f.attname)
            for f in fresh._meta.concrete_fields
            if not getattr(f, "auto_now", False)
        }

    def _pair(self) -> tuple[Any, Any, models.Model, models.Model]:
        owner, intruder = UserFactory(), UserFactory()
        return owner, intruder, self.make(owner), self.make(intruder)

    # --- the contract ------------------------------------------------------------

    def test_anonymous_cannot_list(self):
        if self.list_url is None:
            return
        self.make(UserFactory())
        response = APIClient().get(self.list_url)
        assert response.status_code == 401

    def test_anonymous_cannot_touch_detail(self):
        obj = self.make(UserFactory())
        url = self.detail_url(obj)
        if url is None:
            return
        before = self._snapshot(obj)
        for method in self.detail_methods:
            response = getattr(APIClient(), method)(url, self.update_payload, format="json")
            assert response.status_code == 401, f"{method.upper()} allowed without sign-in"
        assert self._snapshot(obj) == before

    def test_list_contains_only_own_objects(self):
        if self.list_url is None:
            return
        owner, intruder, owned, foreign = self._pair()
        response = client_for(owner).get(self.list_url)
        assert response.status_code == 200
        body = response.json()
        rows = body["results"] if isinstance(body, dict) and "results" in body else body
        ids = {str(row[self.id_field]) for row in rows}
        assert str(owned.pk) in ids
        assert str(foreign.pk) not in ids, "another user's object appeared in the list"

    def test_other_user_cannot_read(self):
        if "get" not in self.detail_methods:
            return
        owner, intruder, owned, _ = self._pair()
        url = self.detail_url(owned)
        if url is None:
            return
        response = client_for(intruder).get(url)
        assert response.status_code == 404, "another user's object was readable"

    def test_other_user_cannot_update(self):
        owner, intruder, owned, _ = self._pair()
        url = self.detail_url(owned)
        if url is None:
            return
        before = self._snapshot(owned)
        for method in ("put", "patch"):
            if method not in self.detail_methods:
                continue
            response = getattr(client_for(intruder), method)(
                url, self.update_payload, format="json"
            )
            assert response.status_code == 404, f"{method.upper()} reached another user's object"
        assert self._snapshot(owned) == before, "another user's object was modified"

    def test_other_user_cannot_delete(self):
        if "delete" not in self.detail_methods:
            return
        owner, intruder, owned, _ = self._pair()
        url = self.detail_url(owned)
        if url is None:
            return
        response = client_for(intruder).delete(url)
        assert response.status_code == 404, "DELETE reached another user's object"
        assert type(owned)._default_manager.filter(pk=owned.pk).exists()

    def test_owner_can_read_own_object(self):
        """Guards against a contract that passes only because everything returns 404."""
        if "get" not in self.detail_methods:
            return
        owner = UserFactory()
        obj = self.make(owner)
        url = self.detail_url(obj)
        if url is None:
            return
        assert client_for(owner).get(url).status_code == 200
