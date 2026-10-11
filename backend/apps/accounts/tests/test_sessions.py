from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.test import APIClient

from tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
CSRF = "/api/v1/auth/csrf"


def credentials(user, password=DEFAULT_PASSWORD):
    return {"email": user.email, "password": password}


class TestLogin:
    def test_signs_in_and_returns_own_account(self, api_client, user):
        response = api_client.post(LOGIN, credentials(user), format="json")

        assert response.status_code == 200
        assert response.json()["id"] == str(user.pk)
        assert response.json()["email"] == user.email
        assert "password" not in response.json()
        assert api_client.get(ME).status_code == 200

    def test_email_is_case_insensitive(self, api_client, user):
        response = api_client.post(
            LOGIN, {"email": user.email.upper(), "password": DEFAULT_PASSWORD}, format="json"
        )
        assert response.status_code == 200

    def test_wrong_password_and_unknown_email_look_the_same(self, api_client, user):
        wrong = api_client.post(LOGIN, credentials(user, "not-the-password"), format="json")
        unknown = api_client.post(
            LOGIN, {"email": "nobody@example.test", "password": DEFAULT_PASSWORD}, format="json"
        )
        assert wrong.status_code == unknown.status_code == 400
        assert wrong.json() == unknown.json()
        assert wrong.json()["code"] == "invalid_credentials"

    def test_unverified_account_cannot_sign_in(self, api_client):
        user = UserFactory(email_verified_at=None)
        response = api_client.post(LOGIN, credentials(user), format="json")
        assert response.status_code == 403
        assert response.json()["code"] == "email_not_verified"
        assert api_client.get(ME).status_code == 401

    def test_deactivated_account_cannot_sign_in(self, api_client):
        user = UserFactory(is_active=False)
        response = api_client.post(LOGIN, credentials(user), format="json")
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_credentials"

    def test_session_key_changes_on_sign_in(self, api_client, user):
        api_client.get(CSRF)
        api_client.session.save()
        before = api_client.session.session_key
        api_client.post(LOGIN, credentials(user), format="json")
        assert api_client.session.session_key != before

    def test_session_cookie_flags(self, api_client, user, settings):
        response = api_client.post(LOGIN, credentials(user), format="json")
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"
        assert int(cookie["max-age"]) == settings.SESSION_COOKIE_AGE


class TestLoginCsrf:
    def test_rejected_without_csrf_token(self, user):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(LOGIN, credentials(user), format="json")
        assert response.status_code == 403
        assert response.json()["code"] == "csrf_failed"

    def test_accepted_with_token_from_csrf_endpoint(self, user):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get(CSRF).json()["csrf_token"]
        response = client.post(LOGIN, credentials(user), format="json", HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 200

    def test_authenticated_writes_need_csrf_too(self, user):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get(CSRF).json()["csrf_token"]
        client.post(LOGIN, credentials(user), format="json", HTTP_X_CSRFTOKEN=token)
        assert client.patch(ME, {"display_name": "x"}, format="json").status_code == 403


class TestLoginThrottling:
    def test_too_many_attempts_from_one_address_are_blocked(self, api_client, user):
        for _ in range(5):
            api_client.post(LOGIN, credentials(user, "wrong-password"), format="json")
        blocked = api_client.post(LOGIN, credentials(user), format="json")

        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
        assert api_client.get(ME).status_code == 401

    def test_attempts_on_one_account_are_blocked_across_addresses(self, user):
        for i in range(10):
            APIClient(REMOTE_ADDR=f"10.0.0.{i + 1}").post(
                LOGIN, credentials(user, "wrong-password"), format="json"
            )
        blocked = APIClient(REMOTE_ADDR="10.0.1.1").post(LOGIN, credentials(user), format="json")
        assert blocked.status_code == 429

    def test_throttle_does_not_store_the_email_address(self, api_client, user):
        from django.core.cache import cache

        api_client.post(LOGIN, credentials(user, "wrong-password"), format="json")
        keys = " ".join(str(k) for k in cache._cache)  # locmem backend in tests
        assert user.email not in keys

    def test_other_accounts_are_unaffected(self, user, other_user):
        for i in range(10):
            APIClient(REMOTE_ADDR=f"10.0.0.{i + 1}").post(
                LOGIN, credentials(user, "wrong-password"), format="json"
            )
        ok = APIClient(REMOTE_ADDR="10.0.2.1").post(LOGIN, credentials(other_user), format="json")
        assert ok.status_code == 200


class TestLogout:
    def test_ends_the_session(self, auth_client):
        assert auth_client.post(LOGOUT).status_code == 204
        assert auth_client.get(ME).status_code == 401

    def test_requires_sign_in(self, api_client):
        assert api_client.post(LOGOUT).status_code == 401

    def test_removes_the_server_side_session(self, auth_client):
        key = auth_client.session.session_key
        auth_client.post(LOGOUT)
        assert not Session.objects.filter(session_key=key).exists()


class TestSessionExpiry:
    def test_expired_session_is_signed_out(self, auth_client):
        key = auth_client.session.session_key
        Session.objects.filter(session_key=key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        assert auth_client.get(ME).status_code == 401

    def test_activity_extends_the_session(self, auth_client):
        key = auth_client.session.session_key
        soon = timezone.now() + timedelta(minutes=5)
        Session.objects.filter(session_key=key).update(expire_date=soon)

        assert auth_client.get(ME).status_code == 200

        assert Session.objects.get(session_key=key).expire_date > soon + timedelta(hours=1)

    def test_clear_expired_sessions_task_removes_old_rows(self, auth_client):
        from apps.accounts.tasks import clear_expired_sessions

        key = auth_client.session.session_key
        Session.objects.filter(session_key=key).update(
            expire_date=timezone.now() - timedelta(days=1)
        )
        clear_expired_sessions.delay()
        assert not Session.objects.filter(session_key=key).exists()


class TestMe:
    def test_requires_sign_in(self, api_client):
        assert api_client.get(ME).status_code == 401
        assert api_client.patch(ME, {"display_name": "x"}, format="json").status_code == 401

    def test_returns_only_expected_fields(self, auth_client):
        assert set(auth_client.get(ME).json()) == {
            "id",
            "email",
            "email_verified",
            "preferred_language",
            "display_name",
            "timezone",
            "created_at",
        }

    def test_updates_preferences(self, auth_client, user):
        response = auth_client.patch(
            ME,
            {"display_name": "Asha", "timezone": "Asia/Dubai", "preferred_language": "hi"},
            format="json",
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.preferred_language == "hi"
        assert user.profile.display_name == "Asha"
        assert user.profile.timezone == "Asia/Dubai"

    def test_rejects_invalid_values(self, auth_client):
        response = auth_client.patch(
            ME, {"timezone": "Nowhere/Land", "preferred_language": "zz"}, format="json"
        )
        assert response.status_code == 400
        assert {"timezone", "preferred_language"} <= set(response.json())

    def test_cannot_change_email_or_privileges(self, auth_client, user):
        original = user.email
        auth_client.patch(
            ME,
            {"email": "attacker@example.test", "is_staff": True, "email_verified": False},
            format="json",
        )
        user.refresh_from_db()
        assert user.email == original
        assert user.is_staff is False
        assert user.email_verified

    def test_one_user_never_sees_or_changes_another(self, auth_client, user, other_user):
        """`me` has no id in the URL, so there is nothing to tamper with."""
        auth_client.patch(ME, {"display_name": "Mine"}, format="json")
        body = auth_client.get(ME).json()

        assert body["id"] == str(user.pk)
        assert other_user.email not in str(body)
        other_user.profile.refresh_from_db()
        assert other_user.profile.display_name == ""
