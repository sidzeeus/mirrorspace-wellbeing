from __future__ import annotations

import re

import pytest
from django.core import mail

from tests.factories import DEFAULT_PASSWORD, UserFactory
from tests.harness import client_for

pytestmark = pytest.mark.django_db

REQUEST = "/api/v1/auth/password-reset"
CONFIRM = "/api/v1/auth/password-reset/confirm"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
NEW_PASSWORD = "an-entirely-new-passphrase"


def parts_from_last_email() -> dict[str, str]:
    match = re.search(r"/reset-password#uid=([^&\s]+)&token=(\S+)", mail.outbox[-1].body)
    assert match, "reset link not found in email"
    return {"uid": match.group(1), "token": match.group(2)}


def request_reset(api_client, user) -> dict[str, str]:
    api_client.post(REQUEST, {"email": user.email}, format="json")
    return parts_from_last_email()


class TestRequest:
    def test_sends_link_to_known_address(self, api_client, user):
        response = api_client.post(REQUEST, {"email": user.email}, format="json")
        assert response.status_code == 200
        assert mail.outbox[0].to == [user.email]

    def test_unknown_address_gets_same_reply_and_no_email(self, api_client, user):
        known = api_client.post(REQUEST, {"email": user.email}, format="json")
        unknown = api_client.post(REQUEST, {"email": "nobody@example.test"}, format="json")
        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        assert len(mail.outbox) == 1

    def test_deactivated_account_gets_no_email(self, api_client):
        user = UserFactory(is_active=False)
        api_client.post(REQUEST, {"email": user.email}, format="json")
        assert mail.outbox == []

    def test_is_rate_limited(self, api_client, user):
        for _ in range(5):
            api_client.post(REQUEST, {"email": user.email}, format="json")
        assert api_client.post(REQUEST, {"email": user.email}, format="json").status_code == 429


class TestConfirm:
    def test_sets_new_password(self, api_client, user):
        parts = request_reset(api_client, user)
        response = api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert not user.check_password(DEFAULT_PASSWORD)

    def test_does_not_sign_the_user_in(self, api_client, user):
        parts = request_reset(api_client, user)
        api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")
        assert api_client.get(ME).status_code == 401

    def test_link_works_only_once(self, api_client, user):
        parts = request_reset(api_client, user)
        api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")
        again = api_client.post(
            CONFIRM, {**parts, "new_password": "yet-another-passphrase"}, format="json"
        )
        assert again.status_code == 400
        assert again.json()["code"] == "invalid_link"
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_existing_sessions_stop_working(self, api_client, user):
        signed_in = client_for(user)
        parts = request_reset(api_client, user)
        api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")
        assert signed_in.get(ME).status_code == 401

    def test_rejects_bad_token_and_bad_uid(self, api_client, user):
        parts = request_reset(api_client, user)
        for bad in (
            {**parts, "token": "wrong-token"},
            {**parts, "uid": "not-base64!"},
            {**parts, "uid": "AAAA"},
        ):
            response = api_client.post(
                CONFIRM, {**bad, "new_password": NEW_PASSWORD}, format="json"
            )
            assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password(DEFAULT_PASSWORD)

    def test_token_for_one_user_cannot_reset_another(self, api_client, user, other_user):
        mine = request_reset(api_client, user)
        theirs = request_reset(api_client, other_user)
        response = api_client.post(
            CONFIRM,
            {"uid": theirs["uid"], "token": mine["token"], "new_password": NEW_PASSWORD},
            format="json",
        )
        assert response.status_code == 400
        other_user.refresh_from_db()
        assert other_user.check_password(DEFAULT_PASSWORD)

    def test_expired_link_is_rejected(self, api_client, user, settings):
        parts = request_reset(api_client, user)
        settings.PASSWORD_RESET_TIMEOUT = -1
        response = api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")
        assert response.status_code == 400

    def test_weak_password_is_rejected_and_link_stays_valid(self, api_client, user):
        parts = request_reset(api_client, user)
        weak = api_client.post(CONFIRM, {**parts, "new_password": "short"}, format="json")
        assert weak.status_code == 400
        assert "new_password" in weak.json()
        ok = api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")
        assert ok.status_code == 200

    def test_reset_confirms_an_unverified_email(self, api_client):
        user = UserFactory(email_verified_at=None)
        parts = request_reset(api_client, user)
        api_client.post(CONFIRM, {**parts, "new_password": NEW_PASSWORD}, format="json")
        login = api_client.post(
            LOGIN, {"email": user.email, "password": NEW_PASSWORD}, format="json"
        )
        assert login.status_code == 200
