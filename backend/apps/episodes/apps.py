from django.apps import AppConfig


class EpisodesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.episodes"
    label = "episodes"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import Episode, Trigger

        register_export(
            "triggers",
            (Trigger,),
            lambda user: [
                {
                    "id": str(trigger.pk),
                    "label": trigger.label,
                    "is_active": trigger.is_active,
                    "preferred_exercises": [e.slug for e in trigger.preferred_exercises.all()],
                    "created_at": trigger.created_at.isoformat(),
                }
                for trigger in Trigger.objects.filter(user=user)
                .prefetch_related("preferred_exercises")
                .order_by("created_at")
            ],
        )
        register_export(
            "episodes",
            (Episode,),
            lambda user: [
                {
                    "id": str(episode.pk),
                    "occurred_at": episode.occurred_at.isoformat(),
                    "intensity": episode.intensity,
                    "duration_minutes": episode.duration_minutes,
                    "trigger_id": str(episode.trigger_id) if episode.trigger_id else None,
                    "helped_exercise": (
                        episode.helped_exercise.slug if episode.helped_exercise else None
                    ),
                    "what_helped": episode.what_helped,
                    "created_at": episode.created_at.isoformat(),
                }
                for episode in Episode.objects.filter(user=user)
                .select_related("helped_exercise")
                .order_by("occurred_at")
            ],
        )
