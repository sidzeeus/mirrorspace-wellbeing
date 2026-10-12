"""Load placeholder knowledge documents:  python manage.py seed_knowledge

Every document is NEEDS_HUMAN_REVIEW and is created as needs_review, so the chat will
not quote it until a qualified reviewer approves it. Safe to run repeatedly; never
changes a document that has been approved or retired. Run `index_knowledge` afterwards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.chat.models import ContentDocument
from apps.wellbeing.models import ReviewStatus

SEED_FILE = Path(__file__).resolve().parent.parent.parent / "seed" / "knowledge.json"
PROTECTED = {ReviewStatus.APPROVED, ReviewStatus.RETIRED}


class Command(BaseCommand):
    help = "Load placeholder knowledge (NEEDS_HUMAN_REVIEW). Never overwrites reviewed content."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        documents = json.loads(SEED_FILE.read_text(encoding="utf-8"))["documents"]
        created = updated = skipped = 0
        for entry in documents:
            slug = entry.pop("slug")
            existing = ContentDocument.objects.filter(slug=slug).first()
            if existing is not None and existing.review_status in PROTECTED:
                skipped += 1
                continue
            _, was_created = ContentDocument.objects.update_or_create(
                slug=slug, defaults={**entry, "review_status": ReviewStatus.NEEDS_REVIEW}
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(
            f"Knowledge: {created} created, {updated} refreshed, {skipped} left untouched "
            "(already reviewed). All loaded documents are NEEDS_HUMAN_REVIEW."
        )
