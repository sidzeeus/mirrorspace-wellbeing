from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from config.fields import EncryptedTextField

MAX_LENGTH = 5000


class VentEntry(models.Model):
    """Something a student chose to keep after venting. Only ever written on request.

    The text is encrypted. No reaction, mood or other label derived from it is stored.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vent_entries"
    )
    body = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="vent_user_recent")]

    def __str__(self) -> str:
        # Never the text: this can end up in logs and error reports.
        return f"VentEntry {self.pk}"
