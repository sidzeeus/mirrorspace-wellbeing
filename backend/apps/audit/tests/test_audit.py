from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit import services
from apps.audit.models import AuditEvent
from apps.sharing.notices import WEEKLY_NOTICE_VERSION
from apps.sharing.weekly import weekly_format_hash
from tests.factories import DEFAULT_PASSWORD, TrustedContactFactory, UserFactory
from tests.harness import client_for

pytestmark = pytest.mark.django_db

CANARY = "CANARY-audit-private-words"


def actions(user=None):
    events = AuditEvent.objects.all() if user is None else AuditEvent.objects.filter(actor=user)
    return list(events.order_by("created_at").values_list("action", flat=True))


class TestRecord:
    def test_stores_who_what_and_which_object(self, user):
        contact = TrustedContactFactory(user=user)
        event = services.record("contact.added", user=user, obj=contact)
        assert (event.actor, event.action) == (user, "contact.added")
        assert (event.object_type, event.object_id) == ("trustedcontact", str(contact.pk))

    def test_unknown_action_is_refused(self, user):
        with pytest.raises(ValueError, match="Unknown audit action"):
            services.record("something.made_up", user=user)

    @pytest.mark.parametrize("key", ["message", "body", "email", "name", "note", "label", "text"])
    def test_metadata_cannot_carry_content(self, user, key):
        with pytest.raises(ValueError, match="not allowed"):
            services.record("consent.granted", user=user, **{key: CANARY})
        assert not AuditEvent.objects.exists()

    def test_allowed_metadata_values_are_kept_short(self, user):
        event = services.record("consent.granted", user=user, reason="x" * 500, scope=["a" * 500])
        assert len(event.metadata["reason"]) == 64
        assert len(event.metadata["scope"][0]) == 64

    def test_model_has_no_free_text_column(self):
        text_columns = [
            f.name for f in AuditEvent._meta.get_fields() if f.get_internal_type() == "TextField"
        ]
        assert text_columns == []


class TestEventsAreRecorded:
    def test_account_lifecycle(self, api_client):
        user = UserFactory(email="lifecycle@example.test")
        api_client.post(
            "/api/v1/auth/login", {"email": user.email, "password": "wrong"}, format="json"
        )
        api_client.post(
            "/api/v1/auth/login", {"email": user.email, "password": DEFAULT_PASSWORD}, format="json"
        )
        api_client.get("/api/v1/export")
        api_client.post("/api/v1/auth/logout")
        api_client.post("/api/v1/auth/password-reset", {"email": user.email}, format="json")

        assert actions(user) == [
            "account.login_failed",
            "account.login",
            "account.export_downloaded",
            "account.logout",
            "account.password_reset_requested",
        ]

    def test_failed_login_for_unknown_address_records_nothing(self, api_client):
        api_client.post(
            "/api/v1/auth/login",
            {"email": "nobody@example.test", "password": "x"},
            format="json",
        )
        assert not AuditEvent.objects.exists()

    def test_registration_and_verification(self, api_client):
        import re

        from django.core import mail

        api_client.post(
            "/api/v1/auth/register",
            {"email": "new@example.test", "password": DEFAULT_PASSWORD, "age_confirmed": True},
            format="json",
        )
        token = re.search(r"#token=(\S+)", mail.outbox[-1].body).group(1)
        api_client.post("/api/v1/auth/verify-email", {"token": token}, format="json")
        assert actions() == ["account.registered", "account.email_verified"]

    def test_full_consent_and_sos_trail(self):
        student = UserFactory(display_name="Asha Rao")
        client = client_for(student)
        contact = TrustedContactFactory(user=student, name=CANARY, email="canary.c@example.test")

        consent_id = client.post(
            "/api/v1/sharing/consent",
            {
                "purpose": "weekly_summary",
                "contact": str(contact.pk),
                "notice_version": WEEKLY_NOTICE_VERSION,
                "preview_hash": weekly_format_hash(),
                "confirmed": True,
            },
            format="json",
        ).json()["id"]
        client.post(f"/api/v1/sharing/consent/{consent_id}/pause")
        client.post(f"/api/v1/sharing/consent/{consent_id}/resume")
        client.post(f"/api/v1/sharing/consent/{consent_id}/confirm")
        client.delete(f"/api/v1/sharing/consent/{consent_id}")
        preview = client.post("/api/v1/sos/preview", {"contact": str(contact.pk)}, format="json")
        client.post(
            "/api/v1/sos/notify-contact",
            {
                "contact": str(contact.pk),
                "message_hash": preview.json()["message_hash"],
                "idempotency_key": str(uuid.uuid4()),
                "confirmed": True,
            },
            format="json",
        )
        client.delete(f"/api/v1/trusted-contacts/{contact.pk}")

        recorded = [a for a in actions(student) if a != "account.login"]
        assert recorded[:5] == [
            "consent.granted",
            "consent.paused",
            "consent.resumed",
            "consent.reconfirmed",
            "consent.revoked",
        ]
        # In tests the send runs inline, so these two can land in either order.
        assert sorted(recorded[5:7]) == ["notification.sent", "sos.requested"]
        assert recorded[7:] == ["contact.removed"]
        granted = AuditEvent.objects.get(action="consent.granted")
        assert granted.metadata == {
            "purpose": "weekly_summary",
            "notice_version": WEEKLY_NOTICE_VERSION,
            "scope": ["display_name", "week_start", "week_end", "check_in_days"],
        }

        dumped = json.dumps(list(AuditEvent.objects.values()), default=str)
        for secret in (
            CANARY,
            "canary.c@example.test",
            "Asha Rao",
            student.email,
            "difficult moment",
        ):
            assert secret not in dumped


class TestPseudonymizeAndPurge:
    def test_pseudonym_is_stable_and_not_the_id(self, user):
        first, second = services.pseudonym(user.pk), services.pseudonym(str(user.pk))
        assert first == second and len(first) == 64
        assert str(user.pk) not in first
        assert services.pseudonym(uuid.uuid4()) != first

    def test_pseudonym_depends_on_the_server_secret(self, user, settings):
        before = services.pseudonym(user.pk)
        settings.PSEUDONYM_KEY = "a-different-secret"
        assert services.pseudonym(user.pk) != before

    def test_pseudonymize_cuts_the_link_and_blanks_object_ids(self, user, other_user):
        contact = TrustedContactFactory(user=user)
        services.record("contact.added", user=user, obj=contact)
        services.record("account.login", user=other_user)

        assert services.pseudonymize_user(user) == 1

        event = AuditEvent.objects.get(action="contact.added")
        assert event.actor is None
        assert event.actor_hash == services.pseudonym(user.pk)
        assert event.object_id == ""
        assert AuditEvent.objects.get(action="account.login").actor == other_user

    def test_events_are_purged_after_the_retention_period(self, user, settings):
        old = services.record("account.login", user=user)
        recent = services.record("account.logout", user=user)
        AuditEvent.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS + 1)
        )

        assert services.purge_expired() == 1
        assert list(AuditEvent.objects.values_list("pk", flat=True)) == [recent.pk]

    def test_retention_is_twelve_months_and_the_purge_is_scheduled(self, settings):
        assert settings.AUDIT_RETENTION_DAYS == 365
        scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
        assert "audit.purge_expired" in scheduled

    def test_purge_task_runs(self, user, settings):
        from apps.audit.tasks import purge_expired

        event = services.record("account.login", user=user)
        AuditEvent.objects.filter(pk=event.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        purge_expired.delay()
        assert not AuditEvent.objects.exists()

    def test_audit_events_are_not_in_the_admin(self):
        from django.contrib import admin

        assert AuditEvent not in admin.site._registry
