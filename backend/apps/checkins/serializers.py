from __future__ import annotations

from datetime import date
from typing import Any

from rest_framework import serializers

from .dates import BACKFILL_DAYS, earliest_allowed, local_today
from .models import METRIC_FIELDS, CheckIn


class CheckInSerializer(serializers.ModelSerializer):
    # Optional. Left out, the server uses today's date in the person's time zone.
    local_date = serializers.DateField(required=False)

    class Meta:
        model = CheckIn
        fields = [
            "id",
            "local_date",
            "timezone",
            "mood",
            "sleep_hours",
            "sleep_quality",
            "energy",
            "stress",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "timezone", "created_at", "updated_at"]
        # Uniqueness per day is handled by the view (a second POST updates the day).
        validators: list = []

    def validate_local_date(self, value: date) -> date:
        if self.instance is not None:
            if value != self.instance.local_date:
                raise serializers.ValidationError("The date of a check-in cannot be changed.")
            return value
        today = local_today(self.context["request"].user)
        if value > today:
            raise serializers.ValidationError("A check-in cannot be dated in the future.")
        if value < earliest_allowed(today):
            raise serializers.ValidationError(
                f"A check-in can be added for the last {BACKFILL_DAYS} days only."
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        values = {
            field: attrs.get(field, getattr(self.instance, field, None)) for field in METRIC_FIELDS
        }
        if all(value is None for value in values.values()):
            raise serializers.ValidationError(
                "Choose at least one value to save, or skip the check-in."
            )
        return attrs
