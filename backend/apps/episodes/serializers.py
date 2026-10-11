from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.wellbeing.models import Exercise

from .models import Episode, Trigger

LABEL_MAX_LENGTH = 80
WHAT_HELPED_MAX_LENGTH = 200
MAX_TRIGGERS = 50
# Allowance for a phone clock that runs slightly fast.
CLOCK_SKEW = timedelta(minutes=5)


class TriggerSerializer(serializers.ModelSerializer):
    # `label` is also an attribute of DRF fields; the declared field wins at run time.
    label = serializers.CharField(  # type: ignore[assignment]
        max_length=LABEL_MAX_LENGTH, trim_whitespace=True
    )
    preferred_exercise_ids = serializers.PrimaryKeyRelatedField(
        source="preferred_exercises",
        many=True,
        required=False,
        queryset=Exercise.objects.none(),
    )

    class Meta:
        model = Trigger
        fields = ["id", "label", "is_active", "preferred_exercise_ids", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        fields["preferred_exercise_ids"].child_relation.queryset = Exercise.objects.visible()  # type: ignore[attr-defined]
        return fields

    def validate_label(self, value: str) -> str:
        # Labels are encrypted, so "already exists" cannot be a database constraint.
        # A person has few triggers, so comparing them here is cheap.
        user = self.context["request"].user
        others = Trigger.objects.filter(user=user)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        elif others.count() >= MAX_TRIGGERS:
            raise serializers.ValidationError(
                f"You can keep up to {MAX_TRIGGERS} triggers. Delete one you no longer use first."
            )
        if any(other.label.casefold() == value.casefold() for other in others):
            raise serializers.ValidationError("You already have a trigger with this name.")
        return value


class EpisodeSerializer(serializers.ModelSerializer):
    trigger = serializers.PrimaryKeyRelatedField(
        queryset=Trigger.objects.none(), allow_null=True, required=False
    )
    helped_exercise = serializers.PrimaryKeyRelatedField(
        queryset=Exercise.objects.none(), allow_null=True, required=False
    )
    what_helped = serializers.CharField(
        max_length=WHAT_HELPED_MAX_LENGTH, allow_blank=True, required=False, trim_whitespace=True
    )

    class Meta:
        model = Episode
        fields = [
            "id",
            "occurred_at",
            "intensity",
            "duration_minutes",
            "trigger",
            "helped_exercise",
            "what_helped",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            # Only the person's own triggers can be attached. Someone else's id is
            # reported as "does not exist", exactly like a made-up one.
            fields["trigger"].queryset = Trigger.objects.filter(user=request.user)  # type: ignore[attr-defined]
        fields["helped_exercise"].queryset = Exercise.objects.visible()  # type: ignore[attr-defined]
        return fields

    def validate_occurred_at(self, value: datetime) -> datetime:
        if value > timezone.now() + CLOCK_SKEW:
            raise serializers.ValidationError("This time is in the future. Choose now or earlier.")
        return value
