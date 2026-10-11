"""Signed tokens for the links a trusted contact receives.

The contact has no account, so the token is their proof. It names one contact row and
one purpose, and it is carried in the URL fragment so it never reaches a server log.
"""

from __future__ import annotations

from django.conf import settings
from django.core import signing

from .models import TrustedContact

_SALT = "sharing.contact-link"
INVITE = "invite"
UNSUBSCRIBE = "unsubscribe"


def make_token(contact: TrustedContact, purpose: str) -> str:
    return signing.dumps({"c": str(contact.pk), "p": purpose}, salt=_SALT)


def contact_from_token(token: str, purpose: str) -> TrustedContact | None:
    # Invitations expire. An unsubscribe link must keep working for as long as the
    # email exists in someone's inbox.
    max_age = settings.CONTACT_INVITATION_MAX_AGE if purpose == INVITE else None
    try:
        payload = signing.loads(token, salt=_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict) or payload.get("p") != purpose:
        return None
    contact_id = payload.get("c")
    if not isinstance(contact_id, str):
        return None
    return TrustedContact.objects.filter(pk=contact_id).select_related("user").first()
