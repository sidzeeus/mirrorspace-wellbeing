"""Support (SOS) messages: explicit, exact, rate limited, never automatic."""

from __future__ import annotations

import uuid

import pytest
from django.core import mail

from apps.audit.models import AuditEvent
from apps.notifications.models import Notification
from apps.sharing.notices import UNSUBSCRIBE_PREVIEW_LINE
from tests.factories import TrustedContactFactory, UserFactory
from tests.harness import client_for

pytestmark = pytest.mark.django_db

PREVIEW = "/api/v1/sos/preview"
SEND = "/api/v1/sos/notify-contact"


@pytest.fixture
def student():
    return UserFactory(display_name="Asha Rao")


@pytest.fixture
def client(student):
    return client_for(student)


@pytest.fixture
def contact(student):
    return TrustedContactFactory(user=student, name="Meera", email="meera@example.test")


def preview(client, contact):
    return client.post(PREVIEW, {"contact": str(contact.pk)}, format="json")


def send_payload(client, contact, /, **overrides):
    data = {
        "contact": str(contact.pk),
        "message_hash": preview(client, contact).json()["message_hash"],
        "idempotency_key": str(uuid.uuid4()),
        "confirmed": True,
    }
    data.update(overrides)
    return data


class TestPreview:
    def test_shows_the_exact_recipient_and_message_and_sends_nothing(self, client, contact):
        response = preview(client, contact)
        body = response.json()

        assert response.status_code == 200
        assert body["recipient"] == {
            "id": str(contact.pk),
            "name": "Meera",
            "email": "meera@example.test",
        }
        assert body["recipient_can_receive"] is True
        assert "Asha Rao" in body["subject"] and "Asha Rao" in body["body"]
        assert body["body"].endswith(UNSUBSCRIBE_PREVIEW_LINE)
        assert len(body["message_hash"]) == 64
        assert "not monitored" in body["limits"]
        assert mail.outbox == []
        assert not Notification.objects.exists()

    def test_backing_out_after_the_preview_leaves_no_trace(self, client, contact):
        """The cancel path: nothing is created until the confirmed send."""
        preview(client, contact)
        preview(client, contact)
        assert not Notification.objects.exists()
        assert not AuditEvent.objects.filter(action="sos.requested").exists()
        assert mail.outbox == []

    def test_only_for_own_contacts(self, client, other_user):
        foreign = TrustedContactFactory(user=other_user, name="Their Contact")
        response = preview(client, foreign)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_contact"
        assert "Their Contact" not in response.content.decode()

    def test_requires_sign_in(self, api_client, contact):
        assert preview(api_client, contact).status_code == 401
        assert api_client.post(SEND, {}, format="json").status_code == 401


class TestSend:
    def test_sends_exactly_what_was_shown_to_exactly_who_was_shown(self, client, contact):
        shown = preview(client, contact).json()

        response = client.post(SEND, send_payload(client, contact), format="json")

        assert response.status_code == 202
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == [shown["recipient"]["email"]]
        assert sent.cc == [] and sent.bcc == []
        assert sent.subject == shown["subject"]
        message, _, footer = sent.body.rpartition("\n\n")
        shown_message, _, shown_footer = shown["body"].rpartition("\n\n")
        assert message == shown_message
        assert shown_footer == UNSUBSCRIBE_PREVIEW_LINE
        assert footer.startswith("To stop receiving these messages: http")

    def test_reply_claims_only_what_is_true(self, client, contact):
        """Non-negotiable 5: never say it was delivered, read, or that help is coming."""
        body = client.post(SEND, send_payload(client, contact), format="json").json()
        text = body["detail"].lower()
        assert "queued" in text
        assert "cannot tell you whether it has been read" in text
        for claim in (
            "delivered",
            "has been sent",
            "was sent",
            "alerted",
            "on their way",
            "monitor",
        ):
            assert claim not in text
        assert set(body) == {"notification_id", "status", "detail"}

    @pytest.mark.parametrize("confirmed", [False, None, "yes please"])
    def test_requires_an_explicit_true_confirmation(self, client, contact, confirmed):
        response = client.post(
            SEND, send_payload(client, contact, confirmed=confirmed), format="json"
        )
        assert response.status_code == 400
        assert mail.outbox == [] and not Notification.objects.exists()

    @pytest.mark.parametrize("missing", ["confirmed", "contact", "message_hash", "idempotency_key"])
    def test_every_part_of_the_request_is_required(self, client, contact, missing):
        payload = send_payload(client, contact)
        del payload[missing]
        assert client.post(SEND, payload, format="json").status_code == 400
        assert mail.outbox == []

    def test_wrong_hash_sends_nothing(self, client, contact):
        response = client.post(
            SEND, send_payload(client, contact, message_hash="0" * 64), format="json"
        )
        assert response.status_code == 400
        assert response.json()["code"] == "preview_outdated"
        assert "Nothing was sent" in response.json()["detail"]
        assert mail.outbox == []

    def test_hash_for_one_contact_cannot_send_to_another(self, client, student, contact):
        second = TrustedContactFactory(user=student)
        payload = send_payload(client, contact, contact=str(second.pk))
        assert client.post(SEND, payload, format="json").json()["code"] == "preview_outdated"
        assert mail.outbox == []

    def test_preview_goes_stale_when_the_message_would_differ(self, client, student, contact):
        payload = send_payload(client, contact)
        client.patch("/api/v1/auth/me", {"display_name": "A different name"}, format="json")
        assert client.post(SEND, payload, format="json").json()["code"] == "preview_outdated"
        assert mail.outbox == []

    def test_cannot_message_another_persons_contact(self, client, other_user):
        foreign = TrustedContactFactory(user=other_user)
        their_hash = (
            preview(client_for(UserFactory(display_name="X")), foreign)
            .json()
            .get("message_hash", "0" * 64)
        )
        response = client.post(
            SEND,
            {
                "contact": str(foreign.pk),
                "message_hash": their_hash,
                "idempotency_key": str(uuid.uuid4()),
                "confirmed": True,
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_contact"
        assert mail.outbox == []

    def test_contact_must_have_agreed(self, client, student):
        pending = TrustedContactFactory(user=student, status="pending")
        response = client.post(SEND, send_payload(client, pending), format="json")
        assert response.json()["code"] == "contact_not_confirmed"
        assert "helpline" in response.json()["detail"]
        assert mail.outbox == []

    def test_double_tap_sends_once(self, client, contact):
        payload = send_payload(client, contact)
        first = client.post(SEND, payload, format="json")
        second = client.post(SEND, payload, format="json")
        assert first.status_code == second.status_code == 202
        assert first.json()["notification_id"] == second.json()["notification_id"]
        assert len(mail.outbox) == 1
        assert AuditEvent.objects.filter(action="sos.requested").count() == 1

    def test_message_text_is_not_kept_after_sending(self, client, contact):
        client.post(SEND, send_payload(client, contact), format="json")
        notification = Notification.objects.get()
        assert (notification.status, notification.body) == ("sent", "")

    def test_student_can_see_the_delivery_status(self, client, contact):
        notification_id = client.post(SEND, send_payload(client, contact), format="json").json()[
            "notification_id"
        ]
        row = client.get(f"/api/v1/notifications/{notification_id}").json()
        assert (row["purpose"], row["status"]) == ("sos", "sent")


class TestLimits:
    def test_hourly_rate_limit(self, client, contact):
        statuses = [
            client.post(SEND, send_payload(client, contact), format="json").status_code
            for _ in range(4)
        ]
        assert statuses == [202, 202, 202, 429]
        assert len(mail.outbox) == 3

    def test_daily_limit_survives_a_cache_reset(self, client, contact, settings):
        from django.core.cache import cache

        settings.SOS_DAILY_LIMIT = 2
        for _ in range(2):
            assert (
                client.post(SEND, send_payload(client, contact), format="json").status_code == 202
            )
        cache.clear()  # the throttle forgets; the database count does not

        response = client.post(SEND, send_payload(client, contact), format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "sos_daily_limit"
        assert "helpline" in response.json()["detail"]
        assert len(mail.outbox) == 2

    def test_one_students_limit_does_not_block_another(self, client, contact, settings):
        settings.SOS_DAILY_LIMIT = 1
        client.post(SEND, send_payload(client, contact), format="json")
        other = UserFactory(display_name="Sam")
        other_contact = TrustedContactFactory(user=other)
        other_client = client_for(other)
        response = other_client.post(SEND, send_payload(other_client, other_contact), format="json")
        assert response.status_code == 202


class TestNeverAutomatic:
    def test_ordinary_activity_never_creates_an_sos(self, client, student, contact):
        """Check-ins at the worst values, a high-intensity episode, a safety plan."""
        client.post("/api/v1/check-ins", {"mood": 1, "stress": 5, "energy": 1}, format="json")
        client.post(
            "/api/v1/episodes",
            {"occurred_at": "2026-01-01T00:00:00Z", "intensity": 5, "what_helped": ""},
            format="json",
        )
        client.put("/api/v1/safety-plan", {"warning_signs": ["everything"]}, format="json")
        client.get("/api/v1/patterns")

        from apps.notifications import services

        services.enqueue_due_weekly()
        services.sweep_stuck()

        assert not Notification.objects.exists()
        assert mail.outbox == []
