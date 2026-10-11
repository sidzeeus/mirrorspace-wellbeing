from rest_framework.throttling import UserRateThrottle

from config.api import IPThrottle


class ContactAddThrottle(UserRateThrottle):
    """Adding a contact or re-sending an invitation emails a third party."""

    scope = "contact_add"


class SosThrottle(UserRateThrottle):
    scope = "sos"


class PublicTokenThrottle(IPThrottle):
    """Endpoints opened from an emailed link by someone without an account."""

    scope = "public_token"
