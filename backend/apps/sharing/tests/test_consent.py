from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications import services as delivery
from apps.notifications.models import Notification
from apps.sharing.models import ConsentRecord
from apps.sharing.notices import PRIVACY_NOTICE_VERSION, WEEKLY_NOTICE_VERSION
from apps.sharing.schedule import next_send_at
from apps.sharing.weekly import ALLOWED_FIELDS, covered_week, weekly_format_hash
from tests.factories import TrustedContactFactory, UserFactory
from tests.harness import OwnedResourceContract, client_for

pytestmark = pytest.mark.django_db

CONSENT = "/api/v1/sharing/consent"
PREVIEW = "/api/v1/sharing/preview"


@pytest.fixture
def student():
    return UserFactory(display_name="Asha Rao")


@pytest.fixture
def client(student):
    return client_for(student)


@pytest.fixture
def contact(student):
    return TrustedContactFactory(user=student, name="Meera", email="meera@example.test")


def grant_payload(contact, /, **overrides):
    data = {
        "purpose": "weekly_summary",
        "contact": str(contact.pk),
        "notice_version": WEEKLY_NOTICE_VERSION,
        "preview_hash": weekly_format_hash(),
        "confirmed": True,
    }
    data.update(overrides)
    return data


def make_consent(user, contact=None, **fields):
    now = timezone.now()
    defaults = {
        "purpose": "weekly_summary",
        "notice_version": WEEKLY_NOTICE_VERSION,
        "granted_at": now,
        "last_confirmed_at": now,
        "send_weekday": 0,
        "send_hour": 9,
    }
    defaults.update(fields)
    return ConsentRecord.objects.create(
        user=user, contact=contact or TrustedContactFactory(user=user), **defaults
    )


class TestConsentIsolation(OwnedResourceContract):
    list_url = CONSENT
    detail_methods = ("get", "delete")

    def make(self, user):
        return make_consent(user)


class TestSharingIsOffByDefault:
    def test_new_account_shares_nothing(self, client, student):
        assert client.get(CONSENT).json()["count"] == 0
        assert client.get("/api/v1/trusted-contacts").json()["count"] == 0
        assert client.get("/api/v1/notifications").json()["count"] == 0

    def test_a_confirmed_contact_alone_triggers_nothing(self, student, contact):
        """Having a contact is not consent. Nothing is planned or sent."""
        assert delivery.enqueue_due_weekly() == 0
        assert not Notification.objects.exists()
        assert mail.outbox == []

    def test_registration_creates_no_consent(self, api_client):
        api_client.post(
            "/api/v1/auth/register",
            {
                "email": "fresh@example.test",
                "password": "correct-horse-battery-staple",
                "age_confirmed": True,
            },
            format="json",
        )
        assert not ConsentRecord.objects.exists()

    def test_model_has_no_default_that_enables_sharing(self):
        field = ConsentRecord._meta.get_field("next_send_at")
        assert field.null and not field.has_default()


class TestPreview:
    def test_shows_the_exact_note_and_what_is_shared(self, client, contact):
        body = client.get(f"{PREVIEW}?contact={contact.pk}").json()

        assert body["recipient"] == {
            "id": str(contact.pk),
            "name": "Meera",
            "email": "meera@example.test",
        }
        assert body["fields_shared"] == list(ALLOWED_FIELDS)
        assert "Asha Rao" in body["subject"] and "Asha Rao" in body["body"]
        assert "checked in 0 of 7 days" in body["body"]
        assert "Silence does not mean anything either way." in body["body"]
        assert "unsubscribe" in body["body"]
        assert body["preview_hash"] == weekly_format_hash()
        assert body["notice_version"] == WEEKLY_NOTICE_VERSION
        assert body["notice"]["never_shared"]

    def test_previewing_turns_nothing_on(self, client, contact):
        client.get(f"{PREVIEW}?contact={contact.pk}")
        assert not ConsentRecord.objects.exists()
        assert mail.outbox == []

    def test_only_for_own_contacts(self, client, other_user):
        foreign = TrustedContactFactory(user=other_user)
        theirs = client.get(f"{PREVIEW}?contact={foreign.pk}")
        unknown = client.get(f"{PREVIEW}?contact=00000000-0000-4000-8000-000000000000")
        garbage = client.get(f"{PREVIEW}?contact=not-a-uuid")
        missing = client.get(PREVIEW)
        for response in (theirs, unknown, garbage, missing):
            assert response.status_code == 400
            assert response.json()["code"] == "invalid_contact"
        assert "foreign" not in theirs.content.decode()


class TestGrant:
    def test_turns_the_weekly_note_on_for_one_contact(self, client, student, contact):
        response = client.post(CONSENT, grant_payload(contact), format="json")
        body = response.json()

        assert response.status_code == 201
        assert body["status"] == "active"
        assert body["scope"] == list(ALLOWED_FIELDS)
        assert body["notice_version"] == WEEKLY_NOTICE_VERSION
        assert (body["send_weekday"], body["send_hour"]) == (0, 9)
        assert body["next_send_at"] is not None
        assert body["granted_at"] == body["last_confirmed_at"]
        # Turning it on does not send anything by itself.
        assert mail.outbox == []

    @pytest.mark.parametrize(
        ("overrides", "expected"),
        [
            ({"confirmed": False}, "confirmed"),
            ({"notice_version": "an-old-version"}, "notice_outdated"),
            ({"preview_hash": "0" * 64}, "preview_outdated"),
            ({"contact": "00000000-0000-4000-8000-000000000000"}, "invalid_contact"),
        ],
    )
    def test_every_condition_is_required(self, client, contact, overrides, expected):
        response = client.post(CONSENT, grant_payload(contact, **overrides), format="json")
        assert response.status_code == 400
        assert expected in str(response.json())
        assert not ConsentRecord.objects.exists()

    @pytest.mark.parametrize("missing", ["confirmed", "contact", "preview_hash", "notice_version"])
    def test_nothing_can_be_left_out(self, client, contact, missing):
        payload = grant_payload(contact)
        del payload[missing]
        assert client.post(CONSENT, payload, format="json").status_code == 400
        assert not ConsentRecord.objects.exists()

    def test_cannot_use_another_persons_contact(self, client, other_user):
        foreign = TrustedContactFactory(user=other_user)
        response = client.post(CONSENT, grant_payload(foreign), format="json")
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_contact"
        assert not ConsentRecord.objects.exists()

    def test_one_live_consent_per_contact(self, client, contact):
        client.post(CONSENT, grant_payload(contact), format="json")
        again = client.post(CONSENT, grant_payload(contact), format="json")
        assert again.json()["code"] == "already_enabled"
        assert ConsentRecord.objects.count() == 1

    def test_schedule_can_be_chosen_within_limits(self, client, contact):
        ok = client.post(
            CONSENT, grant_payload(contact, send_weekday=6, send_hour=0), format="json"
        )
        assert (ok.json()["send_weekday"], ok.json()["send_hour"]) == (6, 0)
        other = TrustedContactFactory(user=contact.user)
        bad = client.post(CONSENT, grant_payload(other, send_weekday=7), format="json")
        assert bad.status_code == 400

    def test_privacy_notice_acceptance_is_recorded_with_its_version(self, client, student):
        ok = client.post(
            CONSENT,
            {
                "purpose": "privacy_notice",
                "notice_version": PRIVACY_NOTICE_VERSION,
                "confirmed": True,
            },
            format="json",
        )
        old = client.post(
            CONSENT,
            {"purpose": "privacy_notice", "notice_version": "old", "confirmed": True},
            format="json",
        )
        assert ok.status_code == 201
        assert ok.json()["contact"] is None and ok.json()["next_send_at"] is None
        assert old.json()["code"] == "notice_outdated"


class TestPauseResumeRevoke:
    @pytest.fixture
    def consent_id(self, client, contact):
        return client.post(CONSENT, grant_payload(contact), format="json").json()["id"]

    def test_pause_stops_the_schedule_and_resume_restarts_it(self, client, consent_id):
        paused = client.post(f"{CONSENT}/{consent_id}/pause").json()
        assert (paused["status"], paused["next_send_at"]) == ("paused", None)
        assert paused["paused_at"] is not None

        resumed = client.post(f"{CONSENT}/{consent_id}/resume").json()
        assert resumed["status"] == "active" and resumed["next_send_at"] is not None
        assert resumed["last_confirmed_at"] > resumed["granted_at"]

    def test_invalid_transitions_are_refused(self, client, consent_id):
        assert client.post(f"{CONSENT}/{consent_id}/resume").json()["code"] == "not_paused"
        client.post(f"{CONSENT}/{consent_id}/pause")
        assert client.post(f"{CONSENT}/{consent_id}/pause").json()["code"] == "not_active"
        assert client.post(f"{CONSENT}/{consent_id}/confirm").json()["code"] == "not_active"

    def test_revoke_is_one_call_keeps_the_row_and_is_repeatable(self, client, consent_id):
        first = client.delete(f"{CONSENT}/{consent_id}")
        second = client.delete(f"{CONSENT}/{consent_id}")

        assert first.status_code == second.status_code == 200
        body = second.json()
        assert (body["status"], body["status_reason"]) == ("revoked", "revoked_by_user")
        assert body["revoked_at"] is not None and body["next_send_at"] is None
        assert first.json()["revoked_at"] == body["revoked_at"]
        assert ConsentRecord.objects.filter(pk=consent_id).exists()

    def test_revoked_consent_cannot_be_resumed(self, client, consent_id):
        client.delete(f"{CONSENT}/{consent_id}")
        assert client.post(f"{CONSENT}/{consent_id}/resume").status_code == 400
        assert ConsentRecord.objects.get(pk=consent_id).status == "revoked"

    def test_can_be_set_up_again_after_revoking(self, client, contact, consent_id):
        client.delete(f"{CONSENT}/{consent_id}")
        again = client.post(CONSENT, grant_payload(contact), format="json")
        assert again.status_code == 201
        history = client.get(CONSENT).json()["results"]
        assert [row["status"] for row in history] == ["active", "revoked"]

    def test_history_shows_version_and_timestamps(self, client, consent_id):
        client.delete(f"{CONSENT}/{consent_id}")
        row = client.get(CONSENT).json()["results"][0]
        assert row["notice_version"] == WEEKLY_NOTICE_VERSION
        assert row["granted_at"] and row["revoked_at"]

    def test_confirm_refreshes_the_confirmation_date(self, client, consent_id):
        ConsentRecord.objects.filter(pk=consent_id).update(
            last_confirmed_at=timezone.now() - timedelta(days=60)
        )
        body = client.post(f"{CONSENT}/{consent_id}/confirm").json()
        assert timezone.now() - datetime.fromisoformat(body["last_confirmed_at"]) < timedelta(
            minutes=1
        )

    def test_consent_cannot_be_edited_directly(self, client, consent_id):
        for method in ("put", "patch"):
            response = getattr(client, method)(
                f"{CONSENT}/{consent_id}", {"status": "active", "scope": ["mood"]}, format="json"
            )
            assert response.status_code == 405


class TestDatabaseGuards:
    def test_an_inactive_consent_can_never_be_scheduled(self, student, contact):
        consent = make_consent(student, contact, status="paused")
        with pytest.raises(IntegrityError), transaction.atomic():
            ConsentRecord.objects.filter(pk=consent.pk).update(next_send_at=timezone.now())

    def test_two_live_consents_for_one_contact_are_impossible(self, student, contact):
        make_consent(student, contact)
        with pytest.raises(IntegrityError), transaction.atomic():
            make_consent(student, contact, status="paused")

    def test_a_revoked_one_does_not_block_a_new_one(self, student, contact):
        make_consent(student, contact, status="revoked")
        make_consent(student, contact)
        assert ConsentRecord.objects.count() == 2


class TestSchedule:
    """The note stays at the same local hour through daylight-saving changes."""

    NEW_YORK = ZoneInfo("America/New_York")
    KOLKATA = ZoneInfo("Asia/Kolkata")

    def local(self, moment, zone):
        return moment.astimezone(zone)

    def test_next_monday_nine_in_india(self):
        after = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)  # a Wednesday
        due = next_send_at(after, self.KOLKATA, weekday=0, hour=9)
        assert self.local(due, self.KOLKATA) == datetime(2026, 5, 18, 9, 0, tzinfo=self.KOLKATA)
        assert due == datetime(2026, 5, 18, 3, 30, tzinfo=UTC)

    def test_same_day_later_hour_is_today_earlier_hour_is_next_week(self):
        monday_8am = datetime(2026, 5, 18, 2, 30, tzinfo=UTC)
        monday_10am = datetime(2026, 5, 18, 4, 30, tzinfo=UTC)
        assert next_send_at(monday_8am, self.KOLKATA, 0, 9).date() == date(2026, 5, 18)
        assert next_send_at(monday_10am, self.KOLKATA, 0, 9) == datetime(
            2026, 5, 25, 3, 30, tzinfo=UTC
        )

    def test_result_is_always_strictly_in_the_future(self):
        exactly_due = datetime(2026, 5, 18, 3, 30, tzinfo=UTC)
        assert next_send_at(exactly_due, self.KOLKATA, 0, 9) > exactly_due

    def test_local_hour_is_kept_across_spring_forward(self):
        before = datetime(2026, 3, 2, 15, 0, tzinfo=UTC)  # Monday before the change
        first = next_send_at(before, self.NEW_YORK, 0, 9)
        second = next_send_at(first, self.NEW_YORK, 0, 9)

        assert self.local(first, self.NEW_YORK).hour == self.local(second, self.NEW_YORK).hour == 9
        # 9 March is after the clocks moved: 09:00 local is 13:00 UTC, not 14:00.
        assert first == datetime(2026, 3, 9, 13, 0, tzinfo=UTC)
        assert second - first == timedelta(days=7)
        earlier = next_send_at(datetime(2026, 2, 24, 0, 0, tzinfo=UTC), self.NEW_YORK, 0, 9)
        assert earlier == datetime(2026, 3, 2, 14, 0, tzinfo=UTC)
        assert first - earlier == timedelta(days=7) - timedelta(hours=1)

    def test_local_hour_is_kept_across_fall_back(self):
        before = datetime(2026, 10, 27, 0, 0, tzinfo=UTC)
        due = next_send_at(before, self.NEW_YORK, 0, 9)  # Monday 2 November, after the change
        assert self.local(due, self.NEW_YORK).hour == 9
        assert due == datetime(2026, 11, 2, 14, 0, tzinfo=UTC)

    def test_an_hour_that_does_not_exist_still_gives_one_send(self):
        # 02:00 on 8 March 2026 is skipped in New York.
        due = next_send_at(datetime(2026, 3, 7, 12, 0, tzinfo=UTC), self.NEW_YORK, 6, 2)
        assert due.astimezone(self.NEW_YORK).date() == date(2026, 3, 8)
        assert next_send_at(due, self.NEW_YORK, 6, 2).astimezone(self.NEW_YORK).date() == date(
            2026, 3, 15
        )

    def test_covered_week_is_the_seven_local_days_before_the_send(self):
        send = datetime(2026, 5, 18, 3, 30, tzinfo=UTC)  # Monday 09:00 IST
        assert covered_week(send, self.KOLKATA) == (date(2026, 5, 11), date(2026, 5, 17))
        # 03:30 UTC is still Sunday evening in New York.
        assert covered_week(send, self.NEW_YORK) == (date(2026, 5, 10), date(2026, 5, 16))

    def test_changing_time_zone_moves_the_next_send(self, client, student, contact):
        consent_id = client.post(CONSENT, grant_payload(contact), format="json").json()["id"]
        before = ConsentRecord.objects.get(pk=consent_id).next_send_at

        client.patch("/api/v1/auth/me", {"timezone": "America/New_York"}, format="json")

        after = ConsentRecord.objects.get(pk=consent_id).next_send_at
        assert after != before
        assert after.astimezone(self.NEW_YORK).hour == 9
        assert after.astimezone(self.NEW_YORK).weekday() == 0
