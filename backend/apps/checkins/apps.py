from django.apps import AppConfig


class CheckinsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.checkins"
    label = "checkins"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import METRIC_FIELDS, CheckIn

        register_export(
            "check_ins",
            (CheckIn,),
            lambda user: [
                {
                    "id": str(row.pk),
                    "local_date": row.local_date.isoformat(),
                    "timezone": row.timezone,
                    **{
                        field: (
                            float(getattr(row, field)) if getattr(row, field) is not None else None
                        )
                        for field in METRIC_FIELDS
                    },
                    "created_at": row.created_at.isoformat(),
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in CheckIn.objects.filter(user=user).order_by("local_date")
            ],
        )
