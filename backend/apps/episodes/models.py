from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from config.fields import EncryptedTextField

INTENSITY_MIN, INTENSITY_MAX = 1, 5
MAX_DURATION_MINUTES = 24 * 60


class Trigger(models.Model):
    """Something the person has noticed tends to come before a hard moment.

    The label is their own words, so it is encrypted at rest and never logged. It is
    not a clinical category and the app attaches no meaning to it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="triggers"
    )
    label = EncryptedTextField()
    # Archived triggers are kept (past episodes still point at them) but not offered.
    is_active = models.BooleanField(default=True)
    preferred_exercises = models.ManyToManyField("wellbeing.Exercise", blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["user", "is_active"], name="episodes_trigger_user_idx")]

    def __str__(self) -> str:
        return f"trigger:{self.pk}"


class Episode(models.Model):
    """A moment the person chose to log: when, how intense, and what helped.

    No diagnostic labels and no free-text description. "What helped" is a short note in
    their own words, encrypted at rest.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="episodes"
    )
    occurred_at = models.DateTimeField()
    intensity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(INTENSITY_MIN), MaxValueValidator(INTENSITY_MAX)]
    )
    duration_minutes = models.PositiveIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(MAX_DURATION_MINUTES)]
    )
    trigger = models.ForeignKey(
        Trigger, null=True, blank=True, on_delete=models.SET_NULL, related_name="episodes"
    )
    helped_exercise = models.ForeignKey(
        "wellbeing.Exercise", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    what_helped = EncryptedTextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(intensity__gte=INTENSITY_MIN, intensity__lte=INTENSITY_MAX),
                name="episodes_episode_intensity_range",
            ),
            models.CheckConstraint(
                condition=Q(duration_minutes__isnull=True)
                | Q(duration_minutes__lte=MAX_DURATION_MINUTES),
                name="episodes_episode_duration_range",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-occurred_at"], name="episodes_user_time_idx"),
        ]

    def __str__(self) -> str:
        return f"episode:{self.pk}"
