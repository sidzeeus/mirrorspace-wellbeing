"""The message a student can choose to send to a trusted contact from Support (SOS).

Non-negotiables 3, 4 and 5:
- Only `request_sos`, called from the student's own confirmed request, creates an SOS
  message. No classifier, schedule, signal or background job does.
- The student is shown the exact recipient and the exact text first. The request must
  quote the hash of what was shown, so what is sent is what was approved.
- The app never says a message was delivered or read, only that it was queued.

NEEDS_HUMAN_REVIEW (docs/review-needed.md R4): the wording below is a placeholder.
The text is fixed. The student cannot edit it, which also means it cannot be used to
send arbitrary content to someone's inbox.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record as audit
from apps.notifications.models import Notification, NotificationPurpose
from apps.notifications.services import create_notification

from .models import ContactStatus, TrustedContact
from .notices import SOS_TEMPLATE_VERSION, UNSUBSCRIBE_PREVIEW_LINE
from .services import display_name_of, fail

SOS_SUBJECT = "{display_name} would like to hear from you"
SOS_BODY = (
    "{display_name} asked {app_name} to send you this message.\n"
    "\n"
    "They are having a difficult moment and would like to hear from you. If you can, "
    "please contact them directly.\n"
    "\n"
    "{display_name} chose to send this themselves. {app_name} is a self-help tool. It is "
    "not monitored, it is not an emergency service, and it knows nothing more about the "
    "situation. If you believe someone is in immediate danger, contact your local "
    "emergency services."
)


@dataclass(frozen=True)
class SosMessage:
    subject: str
    body: str
    message_hash: str


def build_sos_message(user: User, contact: TrustedContact) -> SosMessage:
    params = {"display_name": display_name_of(user), "app_name": settings.APP_NAME}
    subject = SOS_SUBJECT.format(**params)
    body = SOS_BODY.format(**params)
    material = "\n".join([SOS_TEMPLATE_VERSION, str(contact.pk), subject, body])
    return SosMessage(subject, body, hashlib.sha256(material.encode()).hexdigest())


def preview_text(message: SosMessage) -> str:
    """Exactly what the recipient will read, with the unsubscribe link described."""
    return f"{message.body}\n\n{UNSUBSCRIBE_PREVIEW_LINE}"


def request_sos(
    user: User, contact: TrustedContact, *, message_hash: str, idempotency_key: str
) -> tuple[Notification, bool]:
    if contact.user_id != user.pk:
        raise fail("Choose one of your own trusted contacts.", "invalid_contact")
    if contact.status != ContactStatus.CONFIRMED:
        raise fail(
            "This person has not agreed to receive messages, so nothing was sent. "
            "You can call a helpline or open your safety plan instead.",
            "contact_not_confirmed",
        )
    message = build_sos_message(user, contact)
    if message_hash != message.message_hash:
        raise fail(
            "The message or recipient changed since you reviewed it. Nothing was sent. "
            "Review it again.",
            "preview_outdated",
        )
    key = f"sos:{user.pk}:{idempotency_key}"
    existing = Notification.objects.filter(idempotency_key=key).first()
    if existing is not None:
        return existing, False

    since = timezone.now() - timedelta(hours=24)
    sent_today = Notification.objects.filter(
        user=user, purpose=NotificationPurpose.SOS, created_at__gte=since
    ).count()
    if sent_today >= settings.SOS_DAILY_LIMIT:
        raise fail(
            "You have reached the limit for these messages today. You can still call a "
            "helpline or open your safety plan.",
            "sos_daily_limit",
        )

    notification, created = create_notification(
        user=user,
        purpose=NotificationPurpose.SOS,
        contact=contact,
        idempotency_key=key,
        # The approved text, encrypted, kept only until it is sent.
        body=json.dumps({"subject": message.subject, "body": message.body}),
    )
    if created:
        audit("sos.requested", user=user, obj=notification)
    return notification, created
