from typing import Any

from django.apps import AppConfig


class SharingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sharing"
    label = "sharing"

    def ready(self) -> None:
        from django.db.models.signals import post_save

        from apps.accounts.export import register_export
        from apps.accounts.models import Profile

        from .models import ConsentRecord, TrustedContact

        def _iso(value: Any) -> str | None:
            return value.isoformat() if value is not None else None

        register_export(
            "trusted_contacts",
            (TrustedContact,),
            lambda user: [
                {
                    "id": str(contact.pk),
                    "name": contact.name,
                    "email": contact.email,
                    "relationship": contact.relationship,
                    "status": contact.status,
                    "invited_at": _iso(contact.invited_at),
                    "responded_at": _iso(contact.responded_at),
                    "created_at": contact.created_at.isoformat(),
                }
                for contact in TrustedContact.objects.filter(user=user)
            ],
        )
        register_export(
            "consents",
            (ConsentRecord,),
            lambda user: [
                {
                    "id": str(consent.pk),
                    "purpose": consent.purpose,
                    "contact_id": str(consent.contact_id) if consent.contact_id else None,
                    "scope": consent.scope,
                    "notice_version": consent.notice_version,
                    "status": consent.status,
                    "status_reason": consent.status_reason,
                    "granted_at": consent.granted_at.isoformat(),
                    "last_confirmed_at": consent.last_confirmed_at.isoformat(),
                    "paused_at": _iso(consent.paused_at),
                    "revoked_at": _iso(consent.revoked_at),
                    "send_weekday": consent.send_weekday,
                    "send_hour": consent.send_hour,
                }
                for consent in ConsentRecord.objects.filter(user=user).order_by("granted_at")
            ],
        )

        def _reschedule(sender: Any, instance: Profile, **kwargs: Any) -> None:
            # A new time zone moves the local hour the weekly note is due.
            from .services import reschedule_for_user

            reschedule_for_user(instance.user)

        # weak=False: the receiver is a local function, and a weak reference to it would
        # be dropped as soon as ready() returns, silently disconnecting it.
        post_save.connect(
            _reschedule, sender=Profile, dispatch_uid="sharing.reschedule", weak=False
        )
