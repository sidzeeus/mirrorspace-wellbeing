from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import AuditEvent

        register_export(
            "audit_events",
            (AuditEvent,),
            lambda user: [
                {
                    "action": event.action,
                    "object_type": event.object_type,
                    "metadata": event.metadata,
                    "created_at": event.created_at.isoformat(),
                }
                for event in AuditEvent.objects.filter(actor=user).order_by("created_at")
            ],
        )
