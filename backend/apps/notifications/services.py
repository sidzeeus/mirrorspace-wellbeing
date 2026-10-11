"""Creating notifications and delivering them safely.

Guarantees (blueprint section 9), each covered by tests:

1. Consent is re-checked at the moment of sending, not only when the send was planned.
2. A notification is sent at most once. The idempotency key stops a second row being
   created; the pending -> sending step, committed before the provider is called,
   stops a second send if the queue delivers the same task twice or a worker dies.
3. Transient provider errors are retried with growing delays, up to a limit.
4. A permanent bounce stops everything for that address and is visible as a status.
5. Nothing here logs, or passes to the queue, an address or a message body.
"""

from __future__ import annotations

import enum
import logging
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record as audit
from apps.sharing.models import ConsentStatus, ContactStatus
from config.queue import enqueue_on_commit

from . import providers
from .models import Notification, NotificationPurpose, NotificationStatus

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
RETRY_DELAYS = (60, 300, 900, 3600)  # seconds before attempts 2, 3, 4 and 5
STUCK_AFTER = timedelta(minutes=15)


class Outcome(enum.Enum):
    SENT = "sent"
    SKIPPED = "skipped"  # already handled by an earlier delivery of the same task
    CANCELLED = "cancelled"
    RETRY = "retry"
    FAILED = "failed"
    BOUNCED = "bounced"


def create_notification(
    *,
    user: Any,
    purpose: str,
    contact: Any,
    idempotency_key: str,
    consent: Any = None,
    context: dict[str, Any] | None = None,
    body: str = "",
) -> tuple[Notification, bool]:
    """Create the row and queue its delivery. A repeated key returns the first row."""
    from . import tasks

    notification, created = Notification.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "user": user,
            "purpose": purpose,
            "contact": contact,
            "consent": consent,
            "context": context or {},
            "body": body,
            "scheduled_at": timezone.now(),
        },
    )
    if created:
        enqueue_on_commit(tasks.deliver, str(notification.pk))
    return notification, created


def blocked_reason(notification: Notification) -> str:
    """Why this must not be sent right now, or "" if it may. Reads fresh rows."""
    from apps.sharing.services import is_suppressed

    contact = notification.contact
    if contact is None:
        return "contact_removed"
    if not notification.user.is_active:
        return "account_closed"
    if is_suppressed(contact.email_hash):
        return "address_suppressed"

    if notification.purpose == NotificationPurpose.CONTACT_INVITATION:
        return "" if contact.status == ContactStatus.PENDING else "invitation_closed"

    # Everything else needs the contact's own agreement (double opt-in).
    if contact.status != ContactStatus.CONFIRMED:
        return "contact_not_confirmed"

    if notification.purpose == NotificationPurpose.WEEKLY_SUMMARY:
        consent = notification.consent
        if consent is None or consent.status != ConsentStatus.ACTIVE:
            return "consent_inactive"
    return ""


def _finish(notification: Notification, status: str, code: str = "") -> None:
    notification.status = status
    notification.status_code = code
    notification.body = ""  # the approved text is not kept once the outcome is final
    notification.save(update_fields=["status", "status_code", "body", "sent_at", "retry_count"])


def attempt(notification_id: str) -> Outcome:
    """Try to send one notification. Safe to call any number of times."""
    with transaction.atomic():
        notification = (
            Notification.objects.select_for_update(of=("self",))
            .select_related("user", "contact", "consent")
            .filter(pk=notification_id)
            .first()
        )
        if notification is None or notification.status != NotificationStatus.PENDING:
            return Outcome.SKIPPED

        reason = blocked_reason(notification)
        if reason:
            _finish(notification, NotificationStatus.CANCELLED, reason)
            audit("notification.cancelled", user=notification.user, obj=notification, reason=reason)
            logger.info(
                "notification_cancelled",
                extra={"notification_id": notification_id, "reason": reason},
            )
            return Outcome.CANCELLED

        from .render import render

        email = render(notification)
        # Committed before the provider is called: a duplicate delivery of this task
        # now sees "sending" and does nothing.
        notification.status = NotificationStatus.SENDING
        notification.attempted_at = timezone.now()
        notification.save(update_fields=["status", "attempted_at"])

    try:
        reference = providers.send_email(
            to=email.to, subject=email.subject, body=email.body, headers=email.headers
        )
    except providers.PermanentSendError:
        return _record_bounce(notification)
    except providers.TransientSendError:
        return _record_transient_failure(notification)
    except Exception:  # noqa: BLE001 - never let provider details escape into logs
        _finish(notification, NotificationStatus.FAILED, "unexpected_error")
        audit(
            "notification.failed",
            user=notification.user,
            obj=notification,
            reason="unexpected_error",
        )
        logger.error("notification_failed", extra={"notification_id": notification_id})
        return Outcome.FAILED

    notification.provider_reference = reference
    notification.sent_at = timezone.now()
    notification.save(update_fields=["provider_reference"])
    _finish(notification, NotificationStatus.SENT)
    audit(
        "notification.sent", user=notification.user, obj=notification, purpose=notification.purpose
    )
    logger.info(
        "notification_sent",
        extra={"notification_id": notification_id, "purpose": notification.purpose},
    )
    return Outcome.SENT


def _record_transient_failure(notification: Notification) -> Outcome:
    notification.retry_count += 1
    if notification.retry_count >= MAX_ATTEMPTS:
        _finish(notification, NotificationStatus.FAILED, "provider_unavailable")
        audit(
            "notification.failed",
            user=notification.user,
            obj=notification,
            reason="provider_unavailable",
        )
        logger.warning("notification_gave_up", extra={"notification_id": str(notification.pk)})
        return Outcome.FAILED
    notification.status = NotificationStatus.PENDING
    notification.save(update_fields=["status", "retry_count"])
    return Outcome.RETRY


def _record_bounce(notification: Notification) -> Outcome:
    from apps.sharing.services import mark_bounced

    with transaction.atomic():
        _finish(notification, NotificationStatus.BOUNCED, "permanent_bounce")
        if notification.contact is not None:
            mark_bounced(notification.contact)
        audit("notification.bounced", user=notification.user, obj=notification)
    logger.info("notification_bounced", extra={"notification_id": str(notification.pk)})
    return Outcome.BOUNCED


def retry_delay(retry_count: int) -> int:
    return RETRY_DELAYS[min(max(retry_count, 1), len(RETRY_DELAYS)) - 1]


def handle_provider_event(provider_reference: str, event: str) -> bool:
    """A bounce or spam complaint reported later by the provider's webhook."""
    from apps.sharing.services import mark_bounced, unsubscribe

    notification = (
        Notification.objects.select_related("contact", "user")
        .filter(provider_reference=provider_reference)
        .first()
        if provider_reference
        else None
    )
    if notification is None:
        return False
    contact = notification.contact
    if event == "bounced":
        notification.status = NotificationStatus.BOUNCED
        notification.status_code = "permanent_bounce"
        notification.save(update_fields=["status", "status_code"])
        if contact is not None:
            mark_bounced(contact)
        audit("notification.bounced", user=notification.user, obj=notification)
    elif event == "complained" and contact is not None:
        unsubscribe(contact, block_all=True, reason="complaint")
    return True


def enqueue_due_weekly() -> int:
    """Plan a weekly note for every active consent whose time has come.

    The idempotency key is the consent plus the last day of the week covered, so a
    week can only ever produce one note however often this runs.
    """
    from apps.checkins.dates import user_zone
    from apps.sharing.models import ConsentPurpose, ConsentRecord
    from apps.sharing.schedule import next_send_at
    from apps.sharing.services import pause_consent, reconfirmation_due, slot_of
    from apps.sharing.weekly import covered_week

    now = timezone.now()
    due_ids = list(
        ConsentRecord.objects.filter(
            purpose=ConsentPurpose.WEEKLY_SUMMARY,
            status=ConsentStatus.ACTIVE,
            next_send_at__lte=now,
        ).values_list("pk", flat=True)
    )
    planned = 0
    for consent_id in due_ids:
        with transaction.atomic():
            consent = (
                ConsentRecord.objects.select_for_update(of=("self",), skip_locked=True)
                .select_related("user", "contact")
                .filter(pk=consent_id, status=ConsentStatus.ACTIVE, next_send_at__lte=now)
                .first()
            )
            if consent is None or consent.next_send_at is None:
                continue
            if reconfirmation_due(consent):
                pause_consent(consent, reason="reconfirmation_needed")
                continue
            zone = user_zone(consent.user)
            week_start, week_end = covered_week(consent.next_send_at, zone)
            _, created = create_notification(
                user=consent.user,
                purpose=NotificationPurpose.WEEKLY_SUMMARY,
                contact=consent.contact,
                consent=consent,
                idempotency_key=f"weekly:{consent.pk}:{week_end.isoformat()}",
                context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()},
            )
            consent.next_send_at = next_send_at(now, zone, *slot_of(consent))
            consent.save(update_fields=["next_send_at"])
            planned += int(created)
    logger.info("weekly_notes_planned", extra={"count": planned})
    return planned


def sweep_stuck() -> int:
    """Close notifications left in "sending" by a worker that died mid-send.

    We cannot know whether the provider accepted the message, so it is not retried:
    sending twice is worse than a visible "could not confirm" status.
    """
    cutoff = timezone.now() - STUCK_AFTER
    stuck = Notification.objects.filter(status=NotificationStatus.SENDING, attempted_at__lt=cutoff)
    count = 0
    for notification in stuck:
        _finish(notification, NotificationStatus.FAILED, "outcome_unknown")
        count += 1
    return count
