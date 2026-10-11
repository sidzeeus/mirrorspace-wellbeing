from __future__ import annotations

import uuid
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.wellbeing.models import ReviewStatus, visible_statuses
from config.fields import EncryptedJSONField


def _empty_list() -> list[str]:
    return []


class ResourceType(models.TextChoices):
    HELPLINE = "helpline", "Helpline"
    EMERGENCY = "emergency", "Emergency service"
    TEXT_LINE = "text_line", "Text or chat line"
    CAMPUS = "campus", "Campus service"
    ONLINE = "online", "Online resource"


class ResourceQuerySet(models.QuerySet["Resource"]):
    def visible(self) -> ResourceQuerySet:
        return self.filter(status__in=visible_statuses())


class Resource(models.Model):
    """A helpline or support service. Curated by a named human owner, never by code.

    NEEDS_HUMAN_REVIEW: an entry is only shown to students once its status is
    "approved", which means a person checked the number, hours and languages on
    `verified_on`. Entries must be re-verified before every release.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    type = models.CharField(max_length=20, choices=ResourceType.choices)
    # ISO country code, optionally with a subdivision: "IN", "IN-KA".
    region = models.CharField(max_length=10, db_index=True)
    languages = models.JSONField(default=list, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    url = models.URLField(blank=True)
    hours = models.CharField(max_length=120, blank=True)
    # Where the details were checked (an official page), and who is responsible.
    source = models.CharField(max_length=300, blank=True)
    owner = models.CharField(max_length=120, blank=True)
    verified_on = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    # Set by `flag_stale_resources` when the last verification is too old.
    flagged_stale_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ResourceQuerySet.as_manager()

    class Meta:
        ordering = ["region", "type", "name"]

    def __str__(self) -> str:
        return self.slug

    def is_stale(self, today: date | None = None, max_age_days: int | None = None) -> bool:
        """True when nobody has verified this entry recently enough (or ever)."""
        if self.verified_on is None:
            return True
        today = today or timezone.localdate()
        limit = max_age_days if max_age_days is not None else settings.RESOURCE_MAX_AGE_DAYS
        return self.verified_on < today - timedelta(days=limit)


class SafetyPlan(models.Model):
    """A person's own plan for hard moments, in their own words.

    One per person. Everything they write is encrypted at rest. Only the owner can
    read it: there is no admin view, no sharing, and it is never sent anywhere.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safety_plan"
    )
    warning_signs = EncryptedJSONField(default=_empty_list)
    coping_steps = EncryptedJSONField(default=_empty_list)
    people = EncryptedJSONField(default=_empty_list)
    resources = models.ManyToManyField(Resource, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"safety_plan:{self.pk}"
