"""Load placeholder helpline entries:  python manage.py seed_resources

Every entry is NEEDS_HUMAN_REVIEW: created as needs_review with no verification date,
so it is hidden from students until a named person verifies and approves it. Safe to
run repeatedly; never changes an entry that has been approved or retired.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.safety.models import Resource
from apps.wellbeing.models import ReviewStatus

SEED_FILE = Path(__file__).resolve().parent.parent.parent / "seed" / "resources.json"
PROTECTED = {ReviewStatus.APPROVED, ReviewStatus.RETIRED}


class Command(BaseCommand):
    help = "Load placeholder resources (NEEDS_HUMAN_REVIEW). Never overwrites verified entries."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))["resources"]
        created = updated = skipped = 0
        for entry in entries:
            slug = entry.pop("slug")
            existing = Resource.objects.filter(slug=slug).first()
            if existing is not None and existing.status in PROTECTED:
                skipped += 1
                continue
            _, was_created = Resource.objects.update_or_create(
                slug=slug,
                defaults={**entry, "status": ReviewStatus.NEEDS_REVIEW, "verified_on": None},
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(
            f"Resources: {created} created, {updated} refreshed, {skipped} left untouched "
            "(already verified). All loaded entries are NEEDS_HUMAN_REVIEW and unverified."
        )
