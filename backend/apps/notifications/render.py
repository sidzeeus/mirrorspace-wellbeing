"""Builds the email for a notification at the moment it is sent.

NEEDS_HUMAN_REVIEW (docs/review-needed.md R4, R5): invitation wording is a placeholder.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from django.conf import settings

from apps.sharing.models import TrustedContact
from apps.sharing.services import display_name_of
from apps.sharing.tokens import INVITE, UNSUBSCRIBE, make_token
from apps.sharing.weekly import collect_weekly_fields, render_weekly

from .models import Notification, NotificationPurpose


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str
    headers: dict[str, str]


INVITATION_SUBJECT = "{display_name} would like to add you as a trusted contact"
INVITATION_BODY = (
    "{display_name} uses {app_name}, a self-help wellbeing app for students, and would "
    "like to add you as a trusted contact.\n"
    "\n"
    "If you agree, two kinds of email may reach you, and only if {display_name} chooses:\n"
    "- A short weekly note saying how many days they checked in. It contains no "
    "details about how they are.\n"
    "- A message they decide to send you themselves when they would like to hear from "
    "you.\n"
    "\n"
    "{app_name} is not monitored and is not an emergency service. You will not get an "
    "account, and you will not see any of their records.\n"
    "\n"
    "To accept or decline, open this link:\n"
    "{respond_link}\n"
    "\n"
    "If you do nothing, you will not receive any further email. The link works for "
    "{valid_days} days."
)


def unsubscribe_footer(contact: TrustedContact) -> tuple[str, dict[str, str]]:
    token = make_token(contact, UNSUBSCRIBE)
    link = f"{settings.FRONTEND_URL}/unsubscribe#token={token}"
    one_click = f"{settings.API_BASE_URL}/api/v1/unsubscribe/one-click?token={token}"
    headers = {
        "List-Unsubscribe": f"<{one_click}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
    return f"To stop receiving these messages: {link}", headers


def render(notification: Notification) -> OutgoingEmail:
    contact = notification.contact
    assert contact is not None  # noqa: S101 - checked by the caller before rendering
    user = notification.user
    footer, headers = unsubscribe_footer(contact)

    if notification.purpose == NotificationPurpose.CONTACT_INVITATION:
        params = {
            "display_name": display_name_of(user),
            "app_name": settings.APP_NAME,
            "respond_link": (
                f"{settings.FRONTEND_URL}/contact-invitation#token={make_token(contact, INVITE)}"
            ),
            "valid_days": settings.CONTACT_INVITATION_MAX_AGE // 86400,
        }
        subject = INVITATION_SUBJECT.format(**params)
        body = INVITATION_BODY.format(**params)
    elif notification.purpose == NotificationPurpose.WEEKLY_SUMMARY:
        fields = collect_weekly_fields(
            user,
            date.fromisoformat(notification.context["week_start"]),
            date.fromisoformat(notification.context["week_end"]),
        )
        message = render_weekly(fields)
        subject, body = message.subject, message.body
    elif notification.purpose == NotificationPurpose.SOS:
        stored = json.loads(notification.body)
        subject, body = stored["subject"], stored["body"]
    else:  # pragma: no cover - guarded by the model's choices
        raise ValueError("unknown notification purpose")

    return OutgoingEmail(
        to=contact.email, subject=subject, body=f"{body}\n\n{footer}", headers=headers
    )
