from django.apps import AppConfig


class WellbeingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.wellbeing"
    label = "wellbeing"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import ExerciseEvent

        register_export(
            "exercise_events",
            (ExerciseEvent,),
            lambda user: [
                {
                    "id": str(event.pk),
                    "exercise": event.exercise.slug,
                    "kind": event.kind,
                    "created_at": event.created_at.isoformat(),
                }
                for event in ExerciseEvent.objects.filter(user=user)
                .select_related("exercise")
                .order_by("created_at")
            ],
        )
