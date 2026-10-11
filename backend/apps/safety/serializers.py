from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import Resource, SafetyPlan

MAX_ITEMS = 12
MAX_ITEM_LENGTH = 200


class LineListField(serializers.ListField):
    """A short list of the person's own lines. Blank lines are dropped."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            child=serializers.CharField(
                max_length=MAX_ITEM_LENGTH, allow_blank=True, trim_whitespace=True
            ),
            max_length=MAX_ITEMS,
            required=False,
            **kwargs,
        )

    def to_internal_value(self, data: Any) -> list[str]:
        return [line for line in super().to_internal_value(data) if line]


class ResourceSerializer(serializers.ModelSerializer):
    stale = serializers.SerializerMethodField()
    reviewed = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "type",
            "region",
            "languages",
            "phone",
            "url",
            "hours",
            "source",
            "verified_on",
            "stale",
            "reviewed",
        ]

    def get_stale(self, obj: Resource) -> bool:
        return obj.is_stale()

    def get_reviewed(self, obj: Resource) -> bool:
        """False only for unverified placeholders shown in development builds."""
        return obj.status == "approved"


class SafetyPlanSerializer(serializers.ModelSerializer):
    warning_signs = LineListField()
    coping_steps = LineListField()
    people = LineListField()
    resource_ids = serializers.PrimaryKeyRelatedField(
        source="resources", many=True, required=False, queryset=Resource.objects.none()
    )

    class Meta:
        model = SafetyPlan
        fields = ["warning_signs", "coping_steps", "people", "resource_ids", "updated_at"]
        read_only_fields = ["updated_at"]

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        fields["resource_ids"].child_relation.queryset = Resource.objects.visible()  # type: ignore[attr-defined]
        return fields
