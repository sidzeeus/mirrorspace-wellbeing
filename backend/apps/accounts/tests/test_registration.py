from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.core import mail, signing
from django.utils import timezone

from apps.accounts.models import Profile, User
from apps.accounts.tokens import make_email_verification_token
from tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

REGISTER = "/api/v1/auth/register"
VERIFY = "/api/v1/auth/verify-email"
RESEND = "/api/v1/auth/resend-verification"


def payload(**overrides):
    data = {
        "email": "new.student@example.test",
        "password": DEFAULT_PASSWORD,
        "age_confirmed": True,
    }
    data.update(overrides)
    return data


def token_from_last_email() -> str:
    match = re.search(r"/verify-email#token=(\S+)", mail.outbox[-1].body)
    assert match, "verification link not found in email"
    return match.group(1)


class TestRegister:
    def test_creates_unverified_account_and_sends_one_email(self, api_client):
        response = api_client.post(REGISTER, payload(), format="json")

        assert response.status_code == 201
        user = User.objects.get(email="new.student@example.test")
        assert user.email_verified_at is None
        assert user.age_confirmed_at is not None
        assert user.check_password(DEFAULT_PASSWORD)
        assert user.profile.timezone == "Asia/Kolkata"
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["new.student@example.test"]

    def test_response_reveals_nothing_about_the_account(self, api_client):
        response = api_client.post(REGISTER, payload(), format="json")
        assert set(response.json()) == {"detail"}

    def test_does_not_sign_the_user_in(self, api_client):
        api_client.post(REGISTER, payload(), format="json")
        assert api_client.get("/api/v1/auth/me").status_code == 401

    @pytest.mark.parametrize("value", [False, None])
    def test_requires_age_confirmation(self, api_client, value):
        response = api_client.post(REGISTER, payload(age_confirmed=value), format="json")
        assert response.status_code == 400
        assert "age_confirmed" in response.json()
        assert not User.objects.exists()

    def test_age_confirmation_cannot_be_omitted(self, api_client):
        data = payload()
        del data["age_confirmed"]
        response = api_client.post(REGISTER, data, format="json")
        assert response.status_code == 400
        assert not User.objects.exists()

    @pytest.mark.parametrize("password", ["short", "1234567890123", "password123"])
    def test_rejects_weak_passwords(self, api_client, password):
        response = api_client.post(REGISTER, payload(password=password), format="json")
        assert response.status_code == 400
        assert "password" in response.json()

    def test_rejects_invalid_timezone_and_language(self, api_client):
        response = api_client.post(
            REGISTER, payload(timezone="Mars/Olympus", preferred_language="xx"), format="json"
        )
        assert response.status_code == 400
        assert {"timezone", "preferred_language"} <= set(response.json())

    def test_stores_optional_preferences(self, api_client):
        api_client.post(
            REGISTER,
            payload(timezone="Europe/London", preferred_language="hi", display_name="Asha"),
            format="json",
        )
        user = User.objects.get()
        assert user.preferred_language == "hi"
        assert user.profile.timezone == "Europe/London"
        assert user.profile.display_name == "Asha"

    def test_existing_email_gets_identical_response_and_no_second_account(self, api_client):
        existing = UserFactory(email="new.student@example.test")
        fresh = api_client.post(REGISTER, payload(email="someone.else@example.test"), format="json")
        duplicate = api_client.post(
            REGISTER, payload(email="New.Student@Example.TEST"), format="json"
        )

        assert duplicate.status_code == fresh.status_code == 201
        assert duplicate.json() == fresh.json()
        assert User.objects.filter(email__iexact="new.student@example.test").count() == 1
        existing.refresh_from_db()
        assert existing.check_password(DEFAULT_PASSWORD)
        # The real owner is told, by email, that someone tried.
        assert mail.outbox[-1].to == [existing.email]
        assert "already have" in mail.outbox[-1].subject

    def test_email_is_stored_in_lower_case(self, api_client):
        api_client.post(REGISTER, payload(email="MiXed@Example.TEST"), format="json")
        assert User.objects.get().email == "mixed@example.test"

    def test_is_rate_limited(self, api_client):
        for i in range(5):
            api_client.post(REGISTER, payload(email=f"s{i}@example.test"), format="json")
        response = api_client.post(REGISTER, payload(email="s9@example.test"), format="json")
        assert response.status_code == 429


class TestVerifyEmail:
    def test_link_from_email_verifies_the_account(self, api_client):
        api_client.post(REGISTER, payload(), format="json")
        response = api_client.post(VERIFY, {"token": token_from_last_email()}, format="json")

        assert response.status_code == 200
        assert User.objects.get().email_verified_at is not None

    def test_link_puts_token_in_fragment_not_query(self, api_client):
        api_client.post(REGISTER, payload(), format="json")
        link = re.search(r"https?://\S+", mail.outbox[-1].body).group(0)
        assert "?" not in link
        assert "#token=" in link

    def test_using_the_link_twice_is_harmless(self, api_client):
        api_client.post(REGISTER, payload(), format="json")
        token = token_from_last_email()
        api_client.post(VERIFY, {"token": token}, format="json")
        first = User.objects.get().email_verified_at
        again = api_client.post(VERIFY, {"token": token}, format="json")

        assert again.status_code == 200
        assert User.objects.get().email_verified_at == first

    @pytest.mark.parametrize("token", ["garbage", "a:b:c"])
    def test_rejects_forged_token(self, api_client, token):
        response = api_client.post(VERIFY, {"token": token}, format="json")
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_link"

    def test_rejects_token_signed_for_another_purpose(self, api_client):
        user = UserFactory(email_verified_at=None)
        forged = signing.dumps({"u": str(user.pk)}, salt="some.other.purpose")
        assert api_client.post(VERIFY, {"token": forged}, format="json").status_code == 400

    def test_rejects_expired_token(self, api_client, settings):
        user = UserFactory(email_verified_at=None)
        token = make_email_verification_token(user)
        settings.EMAIL_VERIFICATION_MAX_AGE = -1

        response = api_client.post(VERIFY, {"token": token}, format="json")

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.email_verified_at is None

    def test_rejects_token_for_deleted_account(self, api_client):
        user = UserFactory(email_verified_at=None)
        token = make_email_verification_token(user)
        user.delete()
        assert api_client.post(VERIFY, {"token": token}, format="json").status_code == 400


class TestResendVerification:
    def test_sends_again_for_unverified_account(self, api_client):
        user = UserFactory(email_verified_at=None)
        response = api_client.post(RESEND, {"email": user.email}, format="json")
        assert response.status_code == 200
        assert len(mail.outbox) == 1

    def test_same_reply_and_no_email_for_unknown_or_verified(self, api_client):
        verified = UserFactory()
        unverified = UserFactory(email_verified_at=None)

        known = api_client.post(RESEND, {"email": unverified.email}, format="json")
        sent_after_known = len(mail.outbox)
        unknown = api_client.post(RESEND, {"email": "nobody@example.test"}, format="json")
        already = api_client.post(RESEND, {"email": verified.email}, format="json")

        assert known.json() == unknown.json() == already.json()
        assert known.status_code == unknown.status_code == already.status_code == 200
        assert len(mail.outbox) == sent_after_known == 1


class TestUnverifiedCleanup:
    def test_stale_unverified_accounts_are_removed(self, settings):
        from apps.accounts import services

        stale = UserFactory(email_verified_at=None)
        User.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(days=settings.UNVERIFIED_ACCOUNT_TTL_DAYS + 1)
        )
        recent = UserFactory(email_verified_at=None)
        verified_old = UserFactory()
        User.objects.filter(pk=verified_old.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )

        counts = services.purge_stale_accounts()

        assert not User.objects.filter(pk=stale.pk).exists()
        assert not Profile.objects.filter(user_id=stale.pk).exists()
        assert User.objects.filter(pk__in=[recent.pk, verified_old.pk]).count() == 2
        assert counts["erased"] == 0
