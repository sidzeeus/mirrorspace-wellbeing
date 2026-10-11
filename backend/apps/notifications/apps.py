from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import Notification

        register_export(
            "notifications",
            (Notification,),
            lambda user: [
                {
                    "id": str(n.pk),
                    "purpose": n.purpose,
                    "contact_id": str(n.contact_id) if n.contact_id else None,
                    "status": n.status,
                    "status_code": n.status_code,
                    "scheduled_at": n.scheduled_at.isoformat(),
                    "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                }
                for n in Notification.objects.filter(user=user).order_by("scheduled_at")
            ],
        )
