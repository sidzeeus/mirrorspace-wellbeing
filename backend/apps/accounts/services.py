"""Account business logic. Views stay thin and call into here."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit_services
from apps.audit.services import record as audit
from config.queue import enqueue_on_commit

from . import tasks
from .models import User, normalize_email

logger = logging.getLogger(__name__)


def register_user(
    *,
    email: str,
    password: str,
    preferred_language: str,
    timezone_name: str,
    display_name: str,
) -> None:
    """Create an unverified account, or quietly notify the owner if one exists.

    The caller gets the same outcome either way, so registration cannot be used to find
    out whether a particular person has an account here.
    """
    email = normalize_email(email)
    existing = User.objects.filter(email=email).first()
    if existing is not None:
        make_password(password)  # keep the response time similar to the new-account path
        if existing.is_active:
            enqueue_on_commit(tasks.send_account_exists_email, str(existing.pk))
        logger.info("registration_existing_account")
        return

    user = User.objects.create_user(
        email=email,
        password=password,
        preferred_language=preferred_language,
        timezone=timezone_name,
        display_name=display_name,
        age_confirmed_at=timezone.now(),
    )
    enqueue_on_commit(tasks.send_verification_email, str(user.pk))
    audit("account.registered", user=user)
    logger.info("registration_created", extra={"user_id": str(user.pk)})


def record_failed_login(email: str) -> None:
    """Note a failed sign-in against an existing account. The address is not stored."""
    user = User.objects.filter(email=normalize_email(email)).first()
    if user is not None:
        audit("account.login_failed", user=user)


def verify_email(user_id: str) -> bool:
    updated = User.objects.filter(
        pk=user_id, is_active=True, email_verified_at__isnull=True
    ).update(email_verified_at=timezone.now())
    if updated:
        audit("account.email_verified", user=User.objects.get(pk=user_id))
        logger.info("email_verified", extra={"user_id": user_id})
        return True
    return User.objects.filter(pk=user_id, is_active=True).exists()


def request_verification_email(email: str) -> None:
    user = User.objects.filter(
        email=normalize_email(email), is_active=True, email_verified_at__isnull=True
    ).first()
    if user is not None:
        enqueue_on_commit(tasks.send_verification_email, str(user.pk))


def request_password_reset(email: str) -> None:
    user = User.objects.filter(email=normalize_email(email), is_active=True).first()
    if user is not None and user.has_usable_password():
        audit("account.password_reset_requested", user=user)
        enqueue_on_commit(tasks.send_password_reset_email, str(user.pk))


def reset_password(user: User, new_password: str) -> None:
    user.set_password(new_password)
    # Using the emailed link proves control of the address.
    if user.email_verified_at is None:
        user.email_verified_at = timezone.now()
    user.save(update_fields=["password", "email_verified_at"])
    audit("account.password_reset_completed", user=user)
    logger.info("password_reset_completed", extra={"user_id": str(user.pk)})


def request_account_deletion(user: User) -> None:
    """Lock the account now and queue the erase.

    Deactivating first means every other session stops working immediately, even if the
    background erase is delayed.
    """
    user.is_active = False
    user.deletion_requested_at = timezone.now()
    user.save(update_fields=["is_active", "deletion_requested_at"])
    audit("account.deletion_requested", user=user)
    enqueue_on_commit(tasks.erase_account, str(user.pk))
    logger.info("account_deletion_requested", extra={"user_id": str(user.pk)})


def _erase(user: User) -> None:
    """Remove one account for good.

    Rows the user owns go by database cascade. The audit trail is the one exception
    (decision D5): its events are first cut loose from the user and stamped with a
    one-way fingerprint, then kept until the retention period ends.
    """
    from apps.audit.models import AuditEvent

    user_id = str(user.pk)
    audit_services.pseudonymize_user(user)
    AuditEvent.objects.create(action="account.erased", actor_hash=audit_services.pseudonym(user_id))
    user.delete()
    logger.info("account_erased", extra={"user_id": user_id})


@transaction.atomic
def erase_account(user_id: str) -> bool:
    """Permanently remove an account that asked to be deleted."""
    user = (
        User.objects.select_for_update()
        .filter(pk=user_id, deletion_requested_at__isnull=False)
        .first()
    )
    if user is None:
        return False
    _erase(user)
    return True


@transaction.atomic
def purge_stale_accounts() -> dict[str, int]:
    """Sweep for erases whose task was lost, and for accounts that never verified."""
    pending = list(
        User.objects.filter(deletion_requested_at__isnull=False).values_list("pk", flat=True)
    )
    erased = sum(1 for pk in pending if erase_account(str(pk)))

    cutoff = timezone.now() - timedelta(days=settings.UNVERIFIED_ACCOUNT_TTL_DAYS)
    stale = list(
        User.objects.filter(email_verified_at__isnull=True, created_at__lt=cutoff, is_staff=False)
    )
    for user in stale:
        _erase(user)
    counts = {"erased": erased, "unverified_removed": len(stale)}
    logger.info("stale_accounts_purged", extra=counts)
    return counts
