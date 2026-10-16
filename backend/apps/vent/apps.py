from django.apps import AppConfig


class VentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vent"
    label = "vent"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import VentEntry

        register_export(
            "vent_entries",
            (VentEntry,),
            lambda user: [
                {
                    "id": str(entry.pk),
                    "body": entry.body,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in VentEntry.objects.filter(user=user).order_by("created_at")
            ],
        )
