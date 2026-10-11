from __future__ import annotations

import pytest
from django.contrib.sessions.models import Session
from django.utils import timezone

from apps.accounts import services
from apps.accounts.models import Profile, User
from tests.factories import DEFAULT_PASSWORD, UserFactory
from tests.harness import client_for

pytestmark = pytest.mark.django_db

ACCOUNT = "/api/v1/account"
ME = "/api/v1/auth/me"
LOGIN = "/api/v1/auth/login"


class TestDeleteAccount:
    def test_requires_sign_in(self, api_client, user):
        response = api_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")
        assert response.status_code == 401
        assert User.objects.filter(pk=user.pk).exists()

    def test_requires_the_current_password(self, auth_client, user):
        response = auth_client.delete(ACCOUNT, {"password": "wrong-password"}, format="json")
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_password"
        user.refresh_from_db()
        assert user.is_active and user.deletion_requested_at is None
        assert auth_client.get(ME).status_code == 200

    def test_password_cannot_be_omitted(self, auth_client, user):
        assert auth_client.delete(ACCOUNT, {}, format="json").status_code == 400
        assert User.objects.filter(pk=user.pk).exists()

    def test_erases_the_account_and_its_data(self, auth_client, user):
        response = auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")

        assert response.status_code == 202
        assert not User.objects.filter(pk=user.pk).exists()
        assert not Profile.objects.filter(user_id=user.pk).exists()

    def test_signs_out_this_and_every_other_session(self, auth_client, user):
        elsewhere = client_for(user)
        auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")

        assert auth_client.get(ME).status_code == 401
        assert elsewhere.get(ME).status_code == 401

    def test_cannot_sign_in_afterwards(self, auth_client, api_client, user):
        auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")
        response = api_client.post(
            LOGIN, {"email": user.email, "password": DEFAULT_PASSWORD}, format="json"
        )
        assert response.status_code == 400

    def test_other_accounts_are_untouched(self, auth_client, other_user):
        auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")
        other_user.refresh_from_db()
        assert other_user.is_active
        assert Profile.objects.filter(user=other_user).exists()
        assert client_for(other_user).get(ME).status_code == 200

    def test_same_email_can_register_again_after_erasure(self, auth_client, api_client, user):
        auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")
        api_client.post(
            "/api/v1/auth/register",
            {"email": user.email, "password": DEFAULT_PASSWORD, "age_confirmed": True},
            format="json",
        )
        fresh = User.objects.get(email=user.email)
        assert fresh.pk != user.pk
        assert fresh.email_verified_at is None


class TestDeletionWhenTheQueueIsDown:
    """The request must lock the account even if the erase task never runs."""

    @pytest.fixture
    def broken_queue(self, monkeypatch):
        def boom(*args, **kwargs):
            raise ConnectionError("broker unavailable")

        monkeypatch.setattr("apps.accounts.tasks.erase_account.delay", boom)

    def test_account_is_locked_immediately(self, broken_queue, auth_client, user):
        elsewhere = client_for(user)
        response = auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")

        assert response.status_code == 202
        user.refresh_from_db()
        assert user.is_active is False
        assert user.deletion_requested_at is not None
        assert elsewhere.get(ME).status_code == 401

    def test_periodic_sweep_finishes_the_erase(self, broken_queue, auth_client, user, other_user):
        auth_client.delete(ACCOUNT, {"password": DEFAULT_PASSWORD}, format="json")
        counts = services.purge_stale_accounts()

        assert counts["erased"] == 1
        assert not User.objects.filter(pk=user.pk).exists()
        assert User.objects.filter(pk=other_user.pk).exists()


class TestEraseService:
    def test_refuses_to_erase_an_account_that_did_not_ask(self, user):
        assert services.erase_account(str(user.pk)) is False
        assert User.objects.filter(pk=user.pk).exists()

    def test_is_safe_to_run_twice(self):
        user = UserFactory(is_active=False, deletion_requested_at=timezone.now())
        assert services.erase_account(str(user.pk)) is True
        assert services.erase_account(str(user.pk)) is False

    def test_server_side_sessions_of_an_erased_user_are_useless(self, user):
        client = client_for(user)
        key = client.session.session_key
        services.request_account_deletion(user)
        assert client.get(ME).status_code == 401
        # The row may linger until the nightly clean-up, but it authenticates nobody.
        assert Session.objects.filter(session_key=key).count() <= 1
