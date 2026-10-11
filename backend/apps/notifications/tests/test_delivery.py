from __future__ import annotations

import json
import logging
import smtplib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone

from apps.notifications import providers, services, tasks
from apps.notifications.models import Notification, NotificationPurpose, NotificationStatus
from apps.notifications.services import MAX_ATTEMPTS, Outcome
from apps.sharing import services as sharing
from apps.sharing.models import ConsentRecord, SuppressedAddress
from apps.sharing.tokens import UNSUBSCRIBE, make_token
from tests.factories import CheckInFactory, TrustedContactFactory, UserFactory
from tests.harness import OwnedResourceContract, client_for

pytestmark = pytest.mark.django_db

CANARY_NAME = "CANARY-contact-name"
CANARY_EMAIL = "canary.contact@example.test"


@pytest.fixture
def student():
    return UserFactory(display_name="Asha Rao")


@pytest.fixture
def contact(student):
    return TrustedContactFactory(user=student, name=CANARY_NAME, email=CANARY_EMAIL)


@pytest.fixture
def hold_queue(monkeypatch):
    """Stop tasks running inline, and record how each one was queued."""
    queued = []
    monkeypatch.setattr(
        tasks.deliver, "delay", lambda *args, **kwargs: queued.append((args, kwargs))
    )
    monkeypatch.setattr(
        tasks.deliver, "apply_async", lambda *args, **kwargs: queued.append((args, kwargs))
    )
    return queued


def make_consent(student, contact, **fields):
    now = timezone.now()
    defaults = {
        "purpose": "weekly_summary",
        "notice_version": "v",
        "granted_at": now,
        "last_confirmed_at": now,
        "send_weekday": 0,
        "send_hour": 9,
    }
    defaults.update(fields)
    return ConsentRecord.objects.create(user=student, contact=contact, **defaults)


def plan_weekly(student, contact, consent, key="weekly:test"):
    notification, _ = services.create_notification(
        user=student,
        purpose=NotificationPurpose.WEEKLY_SUMMARY,
        contact=contact,
        consent=consent,
        idempotency_key=key,
        context={"week_start": "2026-05-11", "week_end": "2026-05-17"},
    )
    return notification


def fail_with(monkeypatch, error):
    calls = []

    def send(**kwargs):
        calls.append(kwargs)
        raise error

    monkeypatch.setattr(providers, "send_email", send)
    return calls


class TestNotificationIsolation(OwnedResourceContract):
    list_url = "/api/v1/notifications"
    detail_methods = ("get",)

    def make(self, user):
        return Notification.objects.create(
            user=user,
            purpose="sos",
            contact=TrustedContactFactory(user=user),
            idempotency_key=f"iso:{user.pk}",
            scheduled_at=timezone.now(),
        )


class TestConsentIsCheckedAtSendTime:
    def test_active_consent_sends(self, student, contact):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        notification.refresh_from_db()
        assert notification.status == NotificationStatus.SENT
        assert notification.sent_at is not None
        assert len(mail.outbox) == 1 and mail.outbox[0].to == [CANARY_EMAIL]

    @pytest.mark.parametrize("status", ["paused", "revoked"])
    def test_no_email_without_active_consent(self, student, contact, status):
        notification = plan_weekly(student, contact, make_consent(student, contact, status=status))
        notification.refresh_from_db()
        assert (notification.status, notification.status_code) == ("cancelled", "consent_inactive")
        assert mail.outbox == []

    def test_no_email_without_any_consent_row(self, student, contact):
        notification = plan_weekly(student, contact, consent=None)
        notification.refresh_from_db()
        assert notification.status == "cancelled"
        assert mail.outbox == []

    def test_consent_revoked_between_scheduling_and_sending(self, student, contact, hold_queue):
        consent = make_consent(student, contact)
        notification = plan_weekly(student, contact, consent)
        assert len(hold_queue) == 1 and mail.outbox == []

        sharing.revoke_consent(consent)
        outcome = services.attempt(str(notification.pk))

        notification.refresh_from_db()
        assert outcome is Outcome.CANCELLED
        assert (notification.status, notification.status_code) == ("cancelled", "consent_inactive")
        assert mail.outbox == []

    def test_consent_paused_between_scheduling_and_sending(self, student, contact, hold_queue):
        consent = make_consent(student, contact)
        notification = plan_weekly(student, contact, consent)
        sharing.pause_consent(consent)
        assert services.attempt(str(notification.pk)) is Outcome.CANCELLED
        assert mail.outbox == []

    def test_contact_unsubscribed_between_scheduling_and_sending(
        self, student, contact, hold_queue
    ):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        sharing.unsubscribe(contact)
        assert services.attempt(str(notification.pk)) is Outcome.CANCELLED
        assert mail.outbox == []

    def test_contact_removed_between_scheduling_and_sending(self, student, contact, hold_queue):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        sharing.remove_contact(contact)
        assert services.attempt(str(notification.pk)) is Outcome.CANCELLED
        notification.refresh_from_db()
        assert notification.status_code == "contact_removed"
        assert mail.outbox == []

    def test_account_closed_between_scheduling_and_sending(self, student, contact, hold_queue):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        student.is_active = False
        student.save()
        assert services.attempt(str(notification.pk)) is Outcome.CANCELLED
        assert mail.outbox == []

    def test_suppressed_address_is_never_emailed(self, student, contact, hold_queue):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        sharing.suppress(contact.email_hash, "test")
        assert services.attempt(str(notification.pk)) is Outcome.CANCELLED
        assert mail.outbox == []


class TestDuplicatesNeverSendTwice:
    def test_same_idempotency_key_gives_one_row_and_one_email(self, student, contact):
        consent = make_consent(student, contact)
        first = plan_weekly(student, contact, consent, key="weekly:same")
        second = plan_weekly(student, contact, consent, key="weekly:same")
        assert first.pk == second.pk
        assert Notification.objects.count() == 1
        assert len(mail.outbox) == 1

    def test_task_delivered_twice_sends_once(self, student, contact, hold_queue):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        first = services.attempt(str(notification.pk))
        second = services.attempt(str(notification.pk))
        third = services.attempt(str(notification.pk))
        assert (first, second, third) == (Outcome.SENT, Outcome.SKIPPED, Outcome.SKIPPED)
        assert len(mail.outbox) == 1

    def test_worker_that_died_mid_send_is_not_retried(self, student, contact, hold_queue):
        """A row left in "sending" may already have gone out, so it is never re-sent."""
        notification = plan_weekly(student, contact, make_consent(student, contact))
        Notification.objects.filter(pk=notification.pk).update(
            status="sending", attempted_at=timezone.now() - timedelta(hours=1)
        )

        assert services.attempt(str(notification.pk)) is Outcome.SKIPPED
        assert mail.outbox == []

        assert services.sweep_stuck() == 1
        notification.refresh_from_db()
        assert (notification.status, notification.status_code) == ("failed", "outcome_unknown")
        assert services.attempt(str(notification.pk)) is Outcome.SKIPPED

    def test_sweep_leaves_recent_sends_alone(self, student, contact, hold_queue):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        Notification.objects.filter(pk=notification.pk).update(
            status="sending", attempted_at=timezone.now()
        )
        assert services.sweep_stuck() == 0

    def test_unknown_notification_is_ignored(self):
        assert services.attempt("00000000-0000-4000-8000-000000000000") is Outcome.SKIPPED

    def test_idempotency_key_is_unique_in_the_database(self):
        assert Notification._meta.get_field("idempotency_key").unique


class TestRetriesAndBounces:
    def test_transient_error_is_retried_then_succeeds(
        self, student, contact, hold_queue, monkeypatch
    ):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        calls = fail_with(monkeypatch, providers.TransientSendError())

        assert services.attempt(str(notification.pk)) is Outcome.RETRY
        notification.refresh_from_db()
        assert (notification.status, notification.retry_count) == ("pending", 1)
        assert len(calls) == 1

        monkeypatch.undo()
        assert services.attempt(str(notification.pk)) is Outcome.SENT
        assert len(mail.outbox) == 1

    def test_gives_up_after_the_limit_with_a_visible_status(
        self, student, contact, hold_queue, monkeypatch
    ):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        calls = fail_with(monkeypatch, providers.TransientSendError())

        outcomes = [services.attempt(str(notification.pk)) for _ in range(MAX_ATTEMPTS + 2)]

        notification.refresh_from_db()
        assert outcomes[: MAX_ATTEMPTS - 1] == [Outcome.RETRY] * (MAX_ATTEMPTS - 1)
        assert outcomes[MAX_ATTEMPTS - 1] is Outcome.FAILED
        assert outcomes[MAX_ATTEMPTS:] == [Outcome.SKIPPED] * 2
        assert len(calls) == MAX_ATTEMPTS
        assert (notification.status, notification.status_code) == ("failed", "provider_unavailable")

    def test_task_requeues_itself_with_a_growing_delay(
        self, student, contact, hold_queue, monkeypatch
    ):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        fail_with(monkeypatch, providers.TransientSendError())
        hold_queue.clear()

        tasks.deliver.run(str(notification.pk))
        tasks.deliver.run(str(notification.pk))

        delays = [kwargs["countdown"] for _, kwargs in hold_queue]
        assert delays == [60, 300]
        assert all(args == ((str(notification.pk),),) for args, _ in hold_queue)
        assert [services.retry_delay(n) for n in (1, 2, 3, 4, 9)] == [60, 300, 900, 3600, 3600]

    def test_permanent_bounce_stops_everything_for_that_address(
        self, student, contact, hold_queue, monkeypatch
    ):
        consent = make_consent(student, contact)
        notification = plan_weekly(student, contact, consent)
        calls = fail_with(monkeypatch, providers.PermanentSendError())

        assert services.attempt(str(notification.pk)) is Outcome.BOUNCED
        assert services.attempt(str(notification.pk)) is Outcome.SKIPPED

        notification.refresh_from_db()
        contact.refresh_from_db()
        consent.refresh_from_db()
        assert len(calls) == 1  # never retried
        assert (notification.status, notification.status_code) == ("bounced", "permanent_bounce")
        assert contact.status == "bounced"
        assert (consent.status, consent.status_reason) == ("revoked", "bounced")
        assert SuppressedAddress.objects.filter(email_hash=contact.email_hash).exists()

    def test_bounce_is_visible_to_the_student(self, student, contact, hold_queue, monkeypatch):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        fail_with(monkeypatch, providers.PermanentSendError())
        services.attempt(str(notification.pk))

        client = client_for(student)
        row = client.get(f"/api/v1/notifications/{notification.pk}").json()
        assert row["status"] == "bounced"
        assert client.get(f"/api/v1/trusted-contacts/{contact.pk}").json()["status"] == "bounced"

    def test_later_notes_to_a_bounced_address_are_cancelled(
        self, student, contact, hold_queue, monkeypatch
    ):
        consent = make_consent(student, contact)
        first = plan_weekly(student, contact, consent, key="weekly:1")
        fail_with(monkeypatch, providers.PermanentSendError())
        services.attempt(str(first.pk))

        second, _ = services.create_notification(
            user=student,
            purpose=NotificationPurpose.SOS,
            contact=contact,
            idempotency_key="sos:after-bounce",
            body=json.dumps({"subject": "s", "body": "b"}),
        )
        assert services.attempt(str(second.pk)) is Outcome.CANCELLED
        second.refresh_from_db()
        assert second.status == "cancelled"
        assert mail.outbox == []

    def test_unexpected_provider_error_fails_closed_without_leaking(
        self, student, contact, hold_queue, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG)
        notification = plan_weekly(student, contact, make_consent(student, contact))
        fail_with(monkeypatch, RuntimeError(f"relay said no to {CANARY_EMAIL}"))

        assert services.attempt(str(notification.pk)) is Outcome.FAILED
        notification.refresh_from_db()
        assert (notification.status, notification.status_code) == ("failed", "unexpected_error")
        assert CANARY_EMAIL not in caplog.text


class TestProviderAdapter:
    def send(self):
        return providers.send_email(to="x@example.test", subject="s", body="b", headers={})

    def patch_send(self, monkeypatch, error):
        def boom(self, fail_silently=False):
            raise error

        monkeypatch.setattr("django.core.mail.EmailMessage.send", boom)

    def test_returns_a_message_reference(self):
        reference = self.send()
        assert reference.startswith("<") and reference.endswith(">")
        assert mail.outbox[0].extra_headers["Message-ID"] == reference

    @pytest.mark.parametrize(
        "error",
        [
            smtplib.SMTPRecipientsRefused({"x@example.test": (550, b"no such user")}),
            smtplib.SMTPResponseException(554, b"rejected"),
        ],
    )
    def test_hard_failures_are_permanent(self, monkeypatch, error):
        self.patch_send(monkeypatch, error)
        with pytest.raises(providers.PermanentSendError):
            self.send()

    @pytest.mark.parametrize(
        "error",
        [
            smtplib.SMTPRecipientsRefused({"x@example.test": (450, b"mailbox busy")}),
            smtplib.SMTPResponseException(421, b"try later"),
            smtplib.SMTPServerDisconnected("gone"),
            ConnectionRefusedError("down"),
            TimeoutError("slow"),
        ],
    )
    def test_everything_else_is_transient(self, monkeypatch, error):
        self.patch_send(monkeypatch, error)
        with pytest.raises(providers.TransientSendError):
            self.send()

    def test_original_error_text_is_not_carried_along(self, monkeypatch):
        self.patch_send(
            monkeypatch, smtplib.SMTPRecipientsRefused({CANARY_EMAIL: (550, CANARY_EMAIL.encode())})
        )
        with pytest.raises(providers.PermanentSendError) as caught:
            self.send()
        assert CANARY_EMAIL not in str(caught.value)
        assert caught.value.__cause__ is None


class TestWeeklySchedule:
    def due_consent(self, student, contact, when):
        return make_consent(student, contact, next_send_at=when)

    def test_plans_one_note_per_week_however_often_it_runs(self, student, contact, set_now):
        due_at = datetime(2026, 5, 18, 3, 30, tzinfo=UTC)  # Monday 09:00 IST
        set_now(due_at + timedelta(minutes=5))
        consent = self.due_consent(student, contact, due_at)
        for offset in range(3):
            CheckInFactory(user=student, local_date=datetime(2026, 5, 12 + offset).date())

        assert services.enqueue_due_weekly() == 1
        assert services.enqueue_due_weekly() == 0
        assert services.enqueue_due_weekly() == 0

        notification = Notification.objects.get()
        consent.refresh_from_db()
        assert notification.idempotency_key == f"weekly:{consent.pk}:2026-05-17"
        assert notification.context == {"week_start": "2026-05-11", "week_end": "2026-05-17"}
        assert consent.next_send_at == datetime(2026, 5, 25, 3, 30, tzinfo=UTC)
        assert len(mail.outbox) == 1
        assert "checked in 3 of 7 days" in mail.outbox[0].body

    def test_a_replayed_schedule_cannot_send_the_same_week_twice(self, student, contact, set_now):
        due_at = datetime(2026, 5, 18, 3, 30, tzinfo=UTC)
        set_now(due_at + timedelta(minutes=5))
        consent = self.due_consent(student, contact, due_at)
        services.enqueue_due_weekly()

        # Simulate a restored backup or a clock problem putting the due time back.
        ConsentRecord.objects.filter(pk=consent.pk).update(next_send_at=due_at)
        assert services.enqueue_due_weekly() == 0
        assert Notification.objects.count() == 1 and len(mail.outbox) == 1

    def test_not_due_yet_means_nothing_happens(self, student, contact, set_now):
        due_at = datetime(2026, 5, 18, 3, 30, tzinfo=UTC)
        set_now(due_at - timedelta(minutes=1))
        self.due_consent(student, contact, due_at)
        assert services.enqueue_due_weekly() == 0
        assert not Notification.objects.exists()

    def test_week_follows_the_students_time_zone(self, contact, set_now):
        new_yorker = UserFactory(display_name="Sam", timezone="America/New_York")
        their_contact = TrustedContactFactory(user=new_yorker)
        due_at = datetime(2026, 3, 9, 13, 0, tzinfo=UTC)  # Monday 09:00 EDT, after the change
        set_now(due_at + timedelta(minutes=1))
        consent = self.due_consent(new_yorker, their_contact, due_at)

        services.enqueue_due_weekly()

        consent.refresh_from_db()
        assert Notification.objects.get().context == {
            "week_start": "2026-03-02",
            "week_end": "2026-03-08",
        }
        assert consent.next_send_at == datetime(2026, 3, 16, 13, 0, tzinfo=UTC)

    def test_paused_and_revoked_consents_are_never_planned(self, student, contact, set_now):
        set_now(datetime(2026, 5, 18, 4, 0, tzinfo=UTC))
        make_consent(student, contact, status="paused")
        other = TrustedContactFactory(user=student)
        make_consent(student, other, status="revoked")
        assert services.enqueue_due_weekly() == 0
        assert mail.outbox == []

    def test_note_pauses_itself_when_not_reconfirmed(self, student, contact, set_now):
        now = datetime(2026, 5, 18, 4, 0, tzinfo=UTC)
        set_now(now)
        consent = make_consent(
            student,
            contact,
            next_send_at=now - timedelta(minutes=5),
            last_confirmed_at=now - timedelta(days=settings.CONSENT_RECONFIRM_DAYS + 1),
        )

        assert services.enqueue_due_weekly() == 0

        consent.refresh_from_db()
        assert (consent.status, consent.status_reason) == ("paused", "reconfirmation_needed")
        assert consent.next_send_at is None
        assert mail.outbox == []

    def test_beat_schedule_runs_the_planner_and_the_sweeper(self):
        scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
        assert {"notifications.enqueue_due_weekly", "notifications.sweep_stuck"} <= scheduled


class TestNothingSensitiveInQueueOrLogs:
    def test_task_gets_an_id_and_nothing_else(self, student, contact, hold_queue):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        assert hold_queue == [((str(notification.pk),), {})]

    def test_task_names_are_generic(self):
        from config.celery import app

        app.loader.import_default_modules()
        app.autodiscover_tasks(force=True)
        names = [n for n in app.tasks if n.startswith(("notifications.", "audit."))]
        assert sorted(names) == [
            "audit.purge_expired",
            "notifications.deliver",
            "notifications.enqueue_due_weekly",
            "notifications.sweep_stuck",
        ]

    def test_addresses_names_and_bodies_never_reach_the_logs(self, student, contact, caplog):
        caplog.set_level(logging.DEBUG)
        plan_weekly(student, contact, make_consent(student, contact))
        services.create_notification(
            user=student,
            purpose=NotificationPurpose.SOS,
            contact=contact,
            idempotency_key="sos:log-test",
            body=json.dumps({"subject": "CANARY-subject", "body": "CANARY-body-text"}),
        )
        logged = "\n".join(
            f"{r.getMessage()} {json.dumps(r.__dict__, default=str)}" for r in caplog.records
        )
        assert len(mail.outbox) == 2
        for secret in (CANARY_EMAIL, CANARY_NAME, "CANARY-subject", "CANARY-body-text", "Asha Rao"):
            assert secret not in logged

    def test_message_text_is_not_kept_after_sending(self, student, contact):
        notification, _ = services.create_notification(
            user=student,
            purpose=NotificationPurpose.SOS,
            contact=contact,
            idempotency_key="sos:body-test",
            body=json.dumps({"subject": "s", "body": "CANARY-body-text"}),
        )
        notification.refresh_from_db()
        assert notification.status == "sent" and notification.body == ""

    def test_delivery_status_api_has_no_message_text(self, student, contact):
        plan_weekly(student, contact, make_consent(student, contact))
        row = client_for(student).get("/api/v1/notifications").json()["results"][0]
        assert set(row) == {
            "id",
            "purpose",
            "contact",
            "status",
            "status_code",
            "scheduled_at",
            "sent_at",
        }


class TestProviderWebhook:
    URL = "/api/v1/webhooks/email-events"

    def sent(self, student, contact):
        notification = plan_weekly(student, contact, make_consent(student, contact))
        notification.refresh_from_db()
        return notification

    def test_disabled_without_a_secret(self, api_client):
        assert api_client.post(self.URL, {}, format="json").status_code == 404

    def test_wrong_secret_is_refused(self, api_client, settings, student, contact):
        settings.EMAIL_WEBHOOK_SECRET = "s3cret-value"
        notification = self.sent(student, contact)
        body = {"provider_reference": notification.provider_reference, "event": "bounced"}
        assert api_client.post(self.URL, body, format="json").status_code == 403
        wrong = api_client.post(self.URL, body, format="json", HTTP_X_WEBHOOK_SECRET="nope")
        assert wrong.status_code == 403
        contact.refresh_from_db()
        assert contact.status == "confirmed"

    def test_late_bounce_marks_the_contact_and_stops_sending(
        self, api_client, settings, student, contact
    ):
        settings.EMAIL_WEBHOOK_SECRET = "s3cret-value"
        notification = self.sent(student, contact)
        response = api_client.post(
            self.URL,
            {"provider_reference": notification.provider_reference, "event": "bounced"},
            format="json",
            HTTP_X_WEBHOOK_SECRET="s3cret-value",
        )
        notification.refresh_from_db()
        contact.refresh_from_db()
        assert response.json() == {"handled": True}
        assert notification.status == "bounced" and contact.status == "bounced"
        assert not ConsentRecord.objects.filter(status="active").exists()

    def test_spam_complaint_blocks_the_address_everywhere(
        self, api_client, settings, student, contact
    ):
        settings.EMAIL_WEBHOOK_SECRET = "s3cret-value"
        notification = self.sent(student, contact)
        api_client.post(
            self.URL,
            {"provider_reference": notification.provider_reference, "event": "complained"},
            format="json",
            HTTP_X_WEBHOOK_SECRET="s3cret-value",
        )
        contact.refresh_from_db()
        assert contact.status == "unsubscribed"
        assert SuppressedAddress.objects.filter(email_hash=contact.email_hash).exists()

    def test_unknown_reference_changes_nothing(self, api_client, settings):
        settings.EMAIL_WEBHOOK_SECRET = "s3cret-value"
        response = api_client.post(
            self.URL,
            {"provider_reference": "<unknown@x>", "event": "bounced"},
            format="json",
            HTTP_X_WEBHOOK_SECRET="s3cret-value",
        )
        assert response.json() == {"handled": False}


class TestUnsubscribeLinkInEveryEmail:
    def test_weekly_note_link_really_unsubscribes(self, student, contact, api_client):
        import re

        plan_weekly(student, contact, make_consent(student, contact))
        token = re.search(r"/unsubscribe#token=(\S+)", mail.outbox[0].body).group(1)
        assert (
            api_client.post("/api/v1/unsubscribe", {"token": token}, format="json").status_code
            == 200
        )
        contact.refresh_from_db()
        assert contact.status == "unsubscribed"
        assert token == make_token(contact, UNSUBSCRIBE) or len(token) > 20


def test_only_the_sos_module_can_create_an_sos_message():
    """Non-negotiables 3 and 4: no other code path, schedule or signal may send one."""
    apps_dir = Path(settings.BASE_DIR) / "apps"
    allowed = {
        Path("sharing/sos.py"),  # the student's own confirmed request
        Path("sharing/views.py"),  # the endpoint that calls it
        Path("notifications/render.py"),  # turns the stored text into an email
        Path("notifications/models.py"),  # defines the purpose
    }
    offenders = []
    for path in apps_dir.rglob("*.py"):
        relative = path.relative_to(apps_dir)
        if "tests" in relative.parts or "migrations" in relative.parts or relative in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "NotificationPurpose.SOS" in text or "request_sos" in text or "build_sos" in text:
            offenders.append(str(relative))
    assert offenders == []
    scheduled = json.dumps({k: v["task"] for k, v in settings.CELERY_BEAT_SCHEDULE.items()})
    assert "sos" not in scheduled.lower()
