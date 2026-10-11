from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from config.fields import EncryptedTextField


class NotificationPurpose(models.TextChoices):
    CONTACT_INVITATION = "contact_invitation", "Invitation to a trusted contact"
    WEEKLY_SUMMARY = "weekly_summary", "Weekly note"
    SOS = "sos", "Message the student chose to send"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Waiting to be sent"
    SENDING = "sending", "Being sent"
    SENT = "sent", "Handed to the email provider"
    CANCELLED = "cancelled", "Not sent"
    FAILED = "failed", "Could not be sent"
    BOUNCED = "bounced", "Rejected by the recipient's mail server"


class Notification(models.Model):
    """One email to a trusted contact, and what happened to it.

    `idempotency_key` is unique: asking for the same message twice produces one row and
    one email. Weekly and invitation emails are rendered at send time, so no body is
    stored. An SOS message keeps the exact text the student approved, encrypted, and
    only until it is sent.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    purpose = models.CharField(max_length=30, choices=NotificationPurpose.choices)
    contact = models.ForeignKey(
        "sharing.TrustedContact", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    consent = models.ForeignKey(
        "sharing.ConsentRecord", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    idempotency_key = models.CharField(max_length=120, unique=True)
    status = models.CharField(
        max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.PENDING
    )
    # A short machine code such as "consent_inactive". Never an error message.
    status_code = models.CharField(max_length=40, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    provider_reference = models.CharField(max_length=255, blank=True, db_index=True)
    # Non-sensitive parameters, for example the dates of the week covered.
    context = models.JSONField(default=dict, blank=True)
    body = EncryptedTextField(blank=True, default="")
    scheduled_at = models.DateTimeField()
    attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["user", "-scheduled_at"], name="notif_user_time_idx"),
            models.Index(fields=["status", "attempted_at"], name="notif_status_idx"),
        ]

    def __str__(self) -> str:
        return f"notification:{self.pk}"
