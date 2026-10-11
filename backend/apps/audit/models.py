from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):
    """A consent or security event: who did what, to which kind of thing, when.

    It never holds message bodies, email addresses or anything a student wrote.
    `metadata` only accepts a short allow-list of keys (see `services.record`).

    When an account is deleted the link to the user is cut and replaced by a one-way
    fingerprint (`actor_hash`), and every event is purged after the retention period
    (decision D5).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # SET_NULL on purpose: events outlive the account, pseudonymized.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor_hash = models.CharField(max_length=64, blank=True, db_index=True)
    action = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=40, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"audit:{self.action}:{self.pk}"
