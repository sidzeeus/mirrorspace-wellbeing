"""Trusted contacts and consent: the rules for who may be emailed, and when.

Non-negotiable 2: all sharing is off by default, explicit, specific, previewable and
revocable. Nothing in this module turns sharing on by itself.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Profile, User, normalize_email
from apps.audit.services import record as audit
from apps.checkins.dates import user_zone
from config.fields import keyed_hash

from .models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentStatus,
    ContactStatus,
    SuppressedAddress,
    TrustedContact,
)
from .notices import PRIVACY_NOTICE_VERSION, WEEKLY_NOTICE_VERSION
from .schedule import DEFAULT_HOUR, DEFAULT_WEEKDAY, next_send_at
from .weekly import ALLOWED_FIELDS, weekly_format_hash

logger = logging.getLogger(__name__)

MAX_CONTACTS = 3
MAX_INVITATIONS = 3
INVITATION_INTERVAL = timedelta(hours=24)


def fail(message: str, code: str) -> ValidationError:
    return ValidationError({"detail": message, "code": code})


def email_fingerprint(email: str) -> str:
    return keyed_hash("contact-email", normalize_email(email))


def is_suppressed(email_hash: str) -> bool:
    return SuppressedAddress.objects.filter(email_hash=email_hash).exists()


def suppress(email_hash: str, reason: str) -> None:
    SuppressedAddress.objects.get_or_create(email_hash=email_hash, defaults={"reason": reason})


def display_name_of(user: User) -> str:
    return Profile.objects.filter(user=user).values_list("display_name", flat=True).first() or ""


# --- contacts --------------------------------------------------------------------


def add_contact(user: User, *, name: str, email: str, relationship: str = "") -> TrustedContact:
    email = normalize_email(email)
    if not display_name_of(user):
        raise fail(
            "Add a display name in your settings first. The person you invite needs to "
            "know who the invitation is from.",
            "display_name_required",
        )
    if email == user.email:
        raise fail("Choose someone other than yourself.", "own_email")
    if TrustedContact.objects.filter(user=user).count() >= MAX_CONTACTS:
        raise fail(
            f"You can have up to {MAX_CONTACTS} trusted contacts. Remove one to add another.",
            "too_many_contacts",
        )
    fingerprint = email_fingerprint(email)
    if TrustedContact.objects.filter(user=user, email_hash=fingerprint).exists():
        raise fail("You have already added this email address.", "duplicate_contact")

    blocked = is_suppressed(fingerprint)
    contact = TrustedContact.objects.create(
        user=user,
        name=name,
        email=email,
        email_hash=fingerprint,
        relationship=relationship,
        status=ContactStatus.UNAVAILABLE if blocked else ContactStatus.PENDING,
    )
    audit("contact.added", user=user, obj=contact)
    if not blocked:
        send_invitation(contact)
    return contact


def send_invitation(contact: TrustedContact) -> None:
    from apps.notifications.models import NotificationPurpose
    from apps.notifications.services import create_notification

    contact.invite_count += 1
    contact.invited_at = timezone.now()
    contact.save(update_fields=["invite_count", "invited_at"])
    create_notification(
        user=contact.user,
        purpose=NotificationPurpose.CONTACT_INVITATION,
        contact=contact,
        idempotency_key=f"invite:{contact.pk}:{contact.invite_count}",
    )
    audit("contact.invitation_sent", user=contact.user, obj=contact)


def resend_invitation(contact: TrustedContact) -> None:
    if contact.status != ContactStatus.PENDING:
        raise fail("This person has already answered the invitation.", "not_pending")
    if contact.invite_count >= MAX_INVITATIONS:
        raise fail(
            "This invitation has been sent as many times as allowed. If they have not "
            "answered, they may prefer not to.",
            "invitation_limit",
        )
    if contact.invited_at and timezone.now() - contact.invited_at < INVITATION_INTERVAL:
        raise fail("You can send the invitation again after 24 hours.", "invitation_too_soon")
    if is_suppressed(contact.email_hash):
        contact.status = ContactStatus.UNAVAILABLE
        contact.save(update_fields=["status"])
        raise fail("This address cannot receive messages from this app.", "unavailable")
    send_invitation(contact)


def accept_invitation(contact: TrustedContact) -> None:
    """Called by the contact, from the link in their email."""
    if contact.status == ContactStatus.CONFIRMED:
        return
    if contact.status != ContactStatus.PENDING:
        raise fail("This invitation is no longer open.", "invitation_closed")
    contact.status = ContactStatus.CONFIRMED
    contact.responded_at = timezone.now()
    contact.save(update_fields=["status", "responded_at"])
    audit("contact.confirmed", user=contact.user, obj=contact)


def decline_invitation(contact: TrustedContact) -> None:
    if contact.status not in (ContactStatus.PENDING, ContactStatus.DECLINED):
        raise fail("This invitation is no longer open.", "invitation_closed")
    contact.status = ContactStatus.DECLINED
    contact.responded_at = timezone.now()
    contact.save(update_fields=["status", "responded_at"])
    audit("contact.declined", user=contact.user, obj=contact)


@transaction.atomic
def unsubscribe(contact: TrustedContact, *, block_all: bool = False, reason: str = "") -> None:
    """Called by the contact. Stops every message from this student to them at once."""
    contact.status = ContactStatus.UNSUBSCRIBED
    contact.responded_at = timezone.now()
    contact.save(update_fields=["status", "responded_at"])
    _revoke_all_for_contact(contact, "contact_unsubscribed")
    if block_all:
        suppress(contact.email_hash, reason or "unsubscribed")
    audit(
        "contact.unsubscribed",
        user=contact.user,
        obj=contact,
        scope="all" if block_all else "contact",
    )


@transaction.atomic
def mark_bounced(contact: TrustedContact) -> None:
    contact.status = ContactStatus.BOUNCED
    contact.save(update_fields=["status"])
    suppress(contact.email_hash, "bounced")
    _revoke_all_for_contact(contact, "bounced")
    audit("contact.bounced", user=contact.user, obj=contact)


@transaction.atomic
def remove_contact(contact: TrustedContact) -> None:
    _revoke_all_for_contact(contact, "contact_removed")
    audit("contact.removed", user=contact.user, obj=contact)
    contact.delete()


def _revoke_all_for_contact(contact: TrustedContact, reason: str) -> None:
    live = ConsentRecord.objects.filter(
        contact=contact, status__in=[ConsentStatus.ACTIVE, ConsentStatus.PAUSED]
    )
    for consent in live:
        revoke_consent(consent, reason=reason)


# --- consent ---------------------------------------------------------------------


def record_privacy_notice(user: User, notice_version: str) -> ConsentRecord:
    if notice_version != PRIVACY_NOTICE_VERSION:
        raise fail(
            "The notice has been updated. Read the current version before continuing.",
            "notice_outdated",
        )
    now = timezone.now()
    consent = ConsentRecord.objects.create(
        user=user,
        purpose=ConsentPurpose.PRIVACY_NOTICE,
        notice_version=notice_version,
        granted_at=now,
        last_confirmed_at=now,
    )
    audit(
        "consent.granted",
        user=user,
        obj=consent,
        purpose=consent.purpose,
        notice_version=notice_version,
    )
    return consent


@transaction.atomic
def grant_weekly_consent(
    user: User,
    contact: TrustedContact,
    *,
    notice_version: str,
    preview_hash: str,
    send_weekday: int = DEFAULT_WEEKDAY,
    send_hour: int = DEFAULT_HOUR,
) -> ConsentRecord:
    """Turn the weekly note on for one contact.

    Every condition must hold: the contact agreed (double opt-in), the student was
    shown the current notice, and the student was shown the current wording of the
    note (the preview hash). Any mismatch is refused, never guessed.
    """
    if contact.user_id != user.pk:
        raise fail("Choose one of your own trusted contacts.", "invalid_contact")
    if contact.status != ContactStatus.CONFIRMED:
        raise fail(
            "This person has not accepted your invitation yet, so nothing can be sent.",
            "contact_not_confirmed",
        )
    if notice_version != WEEKLY_NOTICE_VERSION:
        raise fail(
            "The notice has been updated. Read the current version before continuing.",
            "notice_outdated",
        )
    if preview_hash != weekly_format_hash():
        raise fail(
            "The message has changed since you previewed it. Preview it again.",
            "preview_outdated",
        )
    if ConsentRecord.objects.filter(
        contact=contact,
        purpose=ConsentPurpose.WEEKLY_SUMMARY,
        status__in=[ConsentStatus.ACTIVE, ConsentStatus.PAUSED],
    ).exists():
        raise fail("The weekly note is already set up for this person.", "already_enabled")

    now = timezone.now()
    consent = ConsentRecord.objects.create(
        user=user,
        contact=contact,
        purpose=ConsentPurpose.WEEKLY_SUMMARY,
        scope=list(ALLOWED_FIELDS),
        notice_version=notice_version,
        granted_at=now,
        last_confirmed_at=now,
        send_weekday=send_weekday,
        send_hour=send_hour,
        next_send_at=next_send_at(now, user_zone(user), send_weekday, send_hour),
    )
    audit(
        "consent.granted",
        user=user,
        obj=consent,
        purpose=consent.purpose,
        notice_version=notice_version,
        scope=list(ALLOWED_FIELDS),
    )
    return consent


def pause_consent(consent: ConsentRecord, *, reason: str = "paused_by_user") -> None:
    if consent.status != ConsentStatus.ACTIVE:
        raise fail("Only an active weekly note can be paused.", "not_active")
    consent.status = ConsentStatus.PAUSED
    consent.status_reason = reason
    consent.paused_at = timezone.now()
    consent.next_send_at = None
    consent.save(update_fields=["status", "status_reason", "paused_at", "next_send_at"])
    audit("consent.paused", user=consent.user, obj=consent, purpose=consent.purpose, reason=reason)


def resume_consent(consent: ConsentRecord) -> None:
    """Resuming is a fresh confirmation by the student."""
    if consent.status != ConsentStatus.PAUSED:
        raise fail("Only a paused weekly note can be resumed.", "not_paused")
    if consent.contact is None or consent.contact.status != ContactStatus.CONFIRMED:
        raise fail("This person can no longer receive messages.", "contact_not_confirmed")
    if consent.notice_version != WEEKLY_NOTICE_VERSION:
        raise fail(
            "The notice has changed. Stop this weekly note and set it up again to continue.",
            "notice_outdated",
        )
    now = timezone.now()
    consent.status = ConsentStatus.ACTIVE
    consent.status_reason = ""
    consent.paused_at = None
    consent.last_confirmed_at = now
    consent.next_send_at = next_send_at(now, user_zone(consent.user), *slot_of(consent))
    consent.save(
        update_fields=["status", "status_reason", "paused_at", "last_confirmed_at", "next_send_at"]
    )
    audit("consent.resumed", user=consent.user, obj=consent, purpose=consent.purpose)


def reconfirm_consent(consent: ConsentRecord) -> None:
    if consent.status != ConsentStatus.ACTIVE:
        raise fail("Only an active weekly note can be confirmed.", "not_active")
    consent.last_confirmed_at = timezone.now()
    consent.save(update_fields=["last_confirmed_at"])
    audit("consent.reconfirmed", user=consent.user, obj=consent, purpose=consent.purpose)


def revoke_consent(consent: ConsentRecord, *, reason: str = "revoked_by_user") -> None:
    """Withdraw consent. Safe to call twice. The row is kept as history."""
    if consent.status == ConsentStatus.REVOKED:
        return
    consent.status = ConsentStatus.REVOKED
    consent.status_reason = reason
    consent.revoked_at = timezone.now()
    consent.next_send_at = None
    consent.save(update_fields=["status", "status_reason", "revoked_at", "next_send_at"])
    audit("consent.revoked", user=consent.user, obj=consent, purpose=consent.purpose, reason=reason)


def slot_of(consent: ConsentRecord) -> tuple[int, int]:
    """The weekday and hour of a weekly note. Hour 0 and Monday (0) are valid values."""
    weekday = consent.send_weekday if consent.send_weekday is not None else DEFAULT_WEEKDAY
    hour = consent.send_hour if consent.send_hour is not None else DEFAULT_HOUR
    return weekday, hour


def reconfirmation_due(consent: ConsentRecord) -> bool:
    limit = timedelta(days=settings.CONSENT_RECONFIRM_DAYS)
    return timezone.now() - consent.last_confirmed_at > limit


def reschedule_for_user(user: User) -> None:
    """Recompute send times after the student changes their time zone."""
    zone = user_zone(user)
    now = timezone.now()
    for consent in ConsentRecord.objects.filter(
        user=user, purpose=ConsentPurpose.WEEKLY_SUMMARY, status=ConsentStatus.ACTIVE
    ):
        consent.next_send_at = next_send_at(now, zone, *slot_of(consent))
        consent.save(update_fields=["next_send_at"])
