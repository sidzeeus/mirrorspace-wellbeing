from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    NEEDS_REVIEW = "needs_review", "Needs human review"
    APPROVED = "approved", "Approved"
    RETIRED = "retired", "Retired"


def visible_statuses() -> list[str]:
    """Review states a student is allowed to see.

    Only content a qualified reviewer approved. In development the unreviewed
    placeholders can be switched on so screens are not empty; production forces the
    switch off (non-negotiable 8).
    """
    if settings.SHOW_UNREVIEWED_CONTENT:
        return [ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVIEW]
    return [ReviewStatus.APPROVED]


class ExerciseCategory(models.TextChoices):
    GROUNDING = "grounding", "Grounding"
    BREATHING = "breathing", "Paced breathing"
    JOURNALING = "journaling", "Journaling"
    PLANNING = "planning", "Planning"
    MOVEMENT = "movement", "Movement"
    WIND_DOWN = "wind_down", "Wind-down"


class ExerciseQuerySet(models.QuerySet["Exercise"]):
    def visible(self) -> ExerciseQuerySet:
        return self.filter(review_status__in=visible_statuses())


class Exercise(models.Model):
    """A short self-help activity. Curated content, never written by students."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    category = models.CharField(max_length=20, choices=ExerciseCategory.choices)
    duration_minutes = models.PositiveSmallIntegerField(default=3)
    # Timing for paced breathing, in seconds, e.g. {"inhale": 4, "exhale": 6}.
    pattern = models.JSONField(default=dict, blank=True)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    version = models.PositiveIntegerField(default=1)
    reviewed_on = models.DateField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExerciseQuerySet.as_manager()

    class Meta:
        ordering = ["category", "slug"]

    def __str__(self) -> str:
        return self.slug


class ExerciseTranslation(models.Model):
    """The words of an exercise in one language, reviewed separately per language."""

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=8, choices=settings.LANGUAGES)
    title = models.CharField(max_length=120)
    summary = models.CharField(max_length=300)
    steps = models.JSONField(default=list)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    reviewed_on = models.DateField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exercise", "language"], name="wellbeing_translation_unique_language"
            )
        ]

    def __str__(self) -> str:
        return f"{self.exercise.slug}:{self.language}"


class ExerciseEventKind(models.TextChoices):
    COMPLETED = "completed", "Completed"
    HELPFUL = "helpful", "Helpful"
    NOT_HELPFUL = "not_helpful", "Not helpful"
    HIDDEN = "hidden", "Hide this"
    UNHIDDEN = "unhidden", "Show again"


class ExerciseEvent(models.Model):
    """Optional feedback from one student about one exercise."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exercise_events"
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=20, choices=ExerciseEventKind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "exercise", "-created_at"], name="wellbeing_event_user_idx"
            )
        ]

    def __str__(self) -> str:
        return f"exercise_event:{self.pk}"
