"""Find helpline entries nobody has verified recently:

    python manage.py flag_stale_resources [--max-age-days 90] [--fail-on-stale]

An entry is stale when it has never been verified or was last verified more than the
given number of days ago. Stale entries are stamped (`flagged_stale_at`) and listed so
the human owner can re-verify them. With --fail-on-stale the command exits with status
1, which lets a scheduled job or a release pipeline stop on it.

The command never edits a phone number and never un-flags an entry: only a person
re-verifying it (setting a new `verified_on`) clears the flag.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.safety.models import Resource
from apps.wellbeing.models import ReviewStatus


class Command(BaseCommand):
    help = "Flag resources whose verification is older than the allowed age."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--max-age-days", type=int, default=settings.RESOURCE_MAX_AGE_DAYS)
        parser.add_argument("--fail-on-stale", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        max_age = options["max_age_days"]
        today = timezone.localdate()
        now = timezone.now()
        stale: list[Resource] = []
        for resource in Resource.objects.exclude(status=ReviewStatus.RETIRED):
            if resource.is_stale(today=today, max_age_days=max_age):
                stale.append(resource)
                if resource.flagged_stale_at is None:
                    Resource.objects.filter(pk=resource.pk).update(flagged_stale_at=now)
            elif resource.flagged_stale_at is not None:
                # Re-verified by a person since it was flagged.
                Resource.objects.filter(pk=resource.pk).update(flagged_stale_at=None)

        if not stale:
            self.stdout.write(f"All resources were verified within {max_age} days.")
            return
        self.stdout.write(f"{len(stale)} resource(s) need re-verification (limit {max_age} days):")
        for resource in stale:
            verified = resource.verified_on.isoformat() if resource.verified_on else "never"
            owner = resource.owner or "no owner assigned"
            self.stdout.write(
                f"  - {resource.slug} [{resource.status}] last verified: {verified}; owner: {owner}"
            )
        if options["fail_on_stale"]:
            raise SystemExit(1)
