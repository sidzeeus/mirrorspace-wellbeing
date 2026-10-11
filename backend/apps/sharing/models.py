from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from config.fields import EncryptedTextField


class ContactStatus(models.TextChoices):
    PENDING = "pending", "Invited, waiting for their answer"
    CONFIRMED = "confirmed", "Agreed to receive messages"
    DECLINED = "declined", "Declined"
    UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
    BOUNCED = "bounced", "Email could not be delivered"
    UNAVAILABLE = "unavailable", "This address cannot receive messages from this app"


class TrustedContact(models.Model):
    """Someone the student chose. Not an account, and they see no student records.

    Name, email and relationship are encrypted at rest. `email_hash` is a keyed
    fingerprint used only to spot duplicates and honour "do not email" requests.
    Nothing is ever sent until the contact has accepted the invitation themselves.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trusted_contacts"
    )
    name = EncryptedTextField()
    email = EncryptedTextField()
    email_hash = models.CharField(max_length=64)
    relationship = EncryptedTextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=ContactStatus.choices, default=ContactStatus.PENDING
    )
    invite_count = models.PositiveSmallIntegerField(default=0)
    invited_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "email_hash"], name="sharing_contact_unique_per_user"
            )
        ]

    def __str__(self) -> str:
        return f"trusted_contact:{self.pk}"

    @property
    def can_receive(self) -> bool:
        return self.status == ContactStatus.CONFIRMED


class SuppressedAddress(models.Model):
    """An address that must never be emailed again by this app, for anyone.

    Stored only as a keyed fingerprint. Created when a contact asks to stop all
    messages, reports one as spam, or their address permanently bounces.
    """

    email_hash = models.CharField(max_length=64, unique=True)
    reason = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"suppressed:{self.pk}"


class ConsentPurpose(models.TextChoices):
    PRIVACY_NOTICE = "privacy_notice", "Read the privacy and safety notice"
    WEEKLY_SUMMARY = "weekly_summary", "Weekly note to a trusted contact"


class ConsentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    REVOKED = "revoked", "Withdrawn"


class ConsentRecord(models.Model):
    """One explicit agreement by the student, for one purpose and one recipient.

    Rows are never deleted while the account exists: withdrawing sets the status and
    `revoked_at`, so the student can always see their own consent history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consents"
    )
    # Kept (as NULL) when the contact is removed, so the history stays complete.
    contact = models.ForeignKey(
        TrustedContact, null=True, blank=True, on_delete=models.SET_NULL, related_name="consents"
    )
    purpose = models.CharField(max_length=30, choices=ConsentPurpose.choices)
    # The exact field names the student agreed to share. Empty for the privacy notice.
    scope = models.JSONField(default=list, blank=True)
    notice_version = models.CharField(max_length=40)
    status = models.CharField(
        max_length=20, choices=ConsentStatus.choices, default=ConsentStatus.ACTIVE
    )
    status_reason = models.CharField(max_length=40, blank=True)
    granted_at = models.DateTimeField()
    last_confirmed_at = models.DateTimeField()
    paused_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    # Weekly schedule in the student's own time zone: 0 is Monday, hour is 0 to 23.
    send_weekday = models.PositiveSmallIntegerField(null=True, blank=True)
    send_hour = models.PositiveSmallIntegerField(null=True, blank=True)
    # The next send, in UTC. NULL whenever the consent is not active.
    next_send_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-granted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "contact", "purpose"],
                condition=Q(status__in=["active", "paused"]),
                name="sharing_consent_one_live_per_contact",
            ),
            models.CheckConstraint(
                condition=Q(send_weekday__isnull=True) | Q(send_weekday__lte=6),
                name="sharing_consent_weekday_range",
            ),
            models.CheckConstraint(
                condition=Q(send_hour__isnull=True) | Q(send_hour__lte=23),
                name="sharing_consent_hour_range",
            ),
            # A consent that is not active can never be scheduled.
            models.CheckConstraint(
                condition=Q(status="active") | Q(next_send_at__isnull=True),
                name="sharing_consent_only_active_is_scheduled",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "next_send_at"], name="sharing_consent_due_idx"),
        ]

    def __str__(self) -> str:
        return f"consent:{self.pk}"
