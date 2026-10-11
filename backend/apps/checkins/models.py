from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

SCALE_MIN, SCALE_MAX = 1, 5
SCALE_FIELDS = ("mood", "sleep_quality", "energy", "stress")
METRIC_FIELDS = ("mood", "sleep_hours", "sleep_quality", "energy", "stress")


def _scale_field() -> models.PositiveSmallIntegerField:
    return models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(SCALE_MIN), MaxValueValidator(SCALE_MAX)],
    )


def _scale_check(field: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(**{f"{field}__isnull": True})
        | Q(**{f"{field}__gte": SCALE_MIN, f"{field}__lte": SCALE_MAX}),
        name=f"checkins_checkin_{field}_range",
    )


class CheckIn(models.Model):
    """One optional, structured check-in per person per local day.

    There is deliberately no free-text note (decision D4). Every value is optional, but
    a row is only stored when at least one was given: skipping stores nothing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="check_ins"
    )
    # The calendar day in the person's own time zone, and the zone used to work it out.
    local_date = models.DateField()
    timezone = models.CharField(max_length=64)
    mood = _scale_field()
    sleep_hours = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    sleep_quality = _scale_field()
    energy = _scale_field()
    stress = _scale_field()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-local_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "local_date"], name="checkins_checkin_one_per_day"
            ),
            *[_scale_check(field) for field in SCALE_FIELDS],
            models.CheckConstraint(
                condition=Q(sleep_hours__isnull=True) | Q(sleep_hours__gte=0, sleep_hours__lte=24),
                name="checkins_checkin_sleep_hours_range",
            ),
            models.CheckConstraint(
                condition=Q(mood__isnull=False)
                | Q(sleep_hours__isnull=False)
                | Q(sleep_quality__isnull=False)
                | Q(energy__isnull=False)
                | Q(stress__isnull=False),
                name="checkins_checkin_not_empty",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-local_date"], name="checkins_user_date_idx"),
        ]

    def __str__(self) -> str:
        return f"check_in:{self.pk}"
