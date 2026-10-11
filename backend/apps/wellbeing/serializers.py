from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework import serializers

from .models import (
    Exercise,
    ExerciseEvent,
    ExerciseEventKind,
    ExerciseTranslation,
    visible_statuses,
)


def pick_translation(exercise: Exercise, language: str) -> ExerciseTranslation | None:
    """The reviewed text in the requested language, falling back to the default one."""
    allowed = set(visible_statuses())
    by_language = {t.language: t for t in exercise.translations.all() if t.review_status in allowed}
    return by_language.get(language) or by_language.get(settings.LANGUAGE_CODE)


class ExerciseSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    reviewed = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = [
            "id",
            "slug",
            "category",
            "duration_minutes",
            "pattern",
            "title",
            "summary",
            "steps",
            "language",
            "hidden",
            "reviewed",
        ]

    def _translation(self, obj: Exercise) -> ExerciseTranslation | None:
        cache: dict[Any, ExerciseTranslation | None] = self.__dict__.setdefault(
            "_translation_cache", {}
        )
        if obj.pk not in cache:
            cache[obj.pk] = pick_translation(obj, self.context.get("language", "en"))
        return cache[obj.pk]

    def get_title(self, obj: Exercise) -> str:
        translation = self._translation(obj)
        return translation.title if translation else ""

    def get_summary(self, obj: Exercise) -> str:
        translation = self._translation(obj)
        return translation.summary if translation else ""

    def get_steps(self, obj: Exercise) -> list[str]:
        translation = self._translation(obj)
        return list(translation.steps) if translation else []

    def get_language(self, obj: Exercise) -> str:
        translation = self._translation(obj)
        return translation.language if translation else ""

    def get_hidden(self, obj: Exercise) -> bool:
        return getattr(obj, "hide_state", None) == ExerciseEventKind.HIDDEN

    def get_reviewed(self, obj: Exercise) -> bool:
        """False only for unreviewed placeholders shown in development builds."""
        translation = self._translation(obj)
        return obj.review_status == "approved" and (
            translation is not None and translation.review_status == "approved"
        )


class ExerciseEventSerializer(serializers.ModelSerializer):
    exercise = serializers.PrimaryKeyRelatedField(queryset=Exercise.objects.none())

    class Meta:
        model = ExerciseEvent
        fields = ["id", "exercise", "kind", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        # Feedback can only be left on content the student is allowed to see.
        fields["exercise"].queryset = Exercise.objects.visible()  # type: ignore[attr-defined]
        return fields
