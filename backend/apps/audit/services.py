"""Recording, pseudonymizing and purging audit events."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from config.fields import keyed_hash

from .models import AuditEvent

logger = logging.getLogger(__name__)

# Every action that may be recorded. A typo fails loudly instead of creating a new,
# unmonitored event name.
ACTIONS = frozenset(
    {
        "account.registered",
        "account.email_verified",
        "account.login",
        "account.login_failed",
        "account.logout",
        "account.password_reset_requested",
        "account.password_reset_completed",
        "account.deletion_requested",
        "account.erased",
        "account.export_downloaded",
        "contact.added",
        "contact.invitation_sent",
        "contact.confirmed",
        "contact.declined",
        "contact.unsubscribed",
        "contact.removed",
        "contact.bounced",
        "consent.granted",
        "consent.paused",
        "consent.resumed",
        "consent.reconfirmed",
        "consent.revoked",
        "sos.requested",
        "notification.sent",
        "notification.cancelled",
        "notification.failed",
        "notification.bounced",
    }
)

# The only metadata keys allowed. All are codes, versions or counts; none can carry
# message text, names or addresses.
ALLOWED_METADATA_KEYS = frozenset({"purpose", "notice_version", "reason", "status", "scope"})
_MAX_VALUE_LENGTH = 64


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    unexpected = set(metadata) - ALLOWED_METADATA_KEYS
    if unexpected:
        raise ValueError(f"Audit metadata keys not allowed: {sorted(unexpected)}")
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            cleaned[key] = [str(item)[:_MAX_VALUE_LENGTH] for item in value[:20]]
        elif isinstance(value, bool | int) or value is None:
            cleaned[key] = value
        else:
            cleaned[key] = str(value)[:_MAX_VALUE_LENGTH]
    return cleaned


def record(
    action: str, *, user: Any = None, obj: models.Model | None = None, **metadata: Any
) -> AuditEvent:
    if action not in ACTIONS:
        raise ValueError(f"Unknown audit action: {action}")
    return AuditEvent.objects.create(
        actor=user if getattr(user, "pk", None) else None,
        action=action,
        object_type=obj._meta.model_name or "" if obj is not None else "",
        object_id=str(obj.pk) if obj is not None else "",
        metadata=_clean_metadata(metadata),
    )


def pseudonym(user_id: Any) -> str:
    return keyed_hash("audit-actor", str(user_id))


def pseudonymize_user(user: Any) -> int:
    """Cut the link between a user and their audit events before the account goes.

    The user id is replaced by a one-way fingerprint, and object ids are blanked
    because they pointed at rows that are about to be deleted.
    """
    return AuditEvent.objects.filter(actor=user).update(
        actor=None, actor_hash=pseudonym(user.pk), object_id=""
    )


def purge_expired() -> int:
    cutoff = timezone.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
    deleted, _ = AuditEvent.objects.filter(created_at__lt=cutoff).delete()
    logger.info("audit_events_purged", extra={"count": deleted})
    return deleted
