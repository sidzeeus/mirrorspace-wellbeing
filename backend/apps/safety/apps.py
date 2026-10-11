from django.apps import AppConfig


class SafetyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.safety"
    label = "safety"

    def ready(self) -> None:
        from apps.accounts.export import register_export

        from .models import SafetyPlan

        def build(user):  # type: ignore[no-untyped-def]
            plan = SafetyPlan.objects.filter(user=user).prefetch_related("resources").first()
            if plan is None:
                return None
            return {
                "warning_signs": plan.warning_signs,
                "coping_steps": plan.coping_steps,
                "people": plan.people,
                "resources": [resource.slug for resource in plan.resources.all()],
                "updated_at": plan.updated_at.isoformat(),
            }

        register_export("safety_plan", (SafetyPlan,), build)
