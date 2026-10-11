"""Load the sample exercises:  python manage.py seed_exercises

Everything loaded is placeholder content flagged NEEDS_HUMAN_REVIEW. It is created with
review_status=needs_review and is therefore hidden from students until a qualified
reviewer approves it. The command is safe to run repeatedly and never touches an
exercise or translation that has already been approved or retired.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.wellbeing.models import Exercise, ExerciseTranslation, ReviewStatus

SEED_FILE = Path(__file__).resolve().parent.parent.parent / "seed" / "exercises.json"
PROTECTED = {ReviewStatus.APPROVED, ReviewStatus.RETIRED}


class Command(BaseCommand):
    help = "Load placeholder exercises (NEEDS_HUMAN_REVIEW). Never overwrites approved content."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))["exercises"]
        created = updated = skipped = 0
        for entry in entries:
            exercise = Exercise.objects.filter(slug=entry["slug"]).first()
            if exercise is not None and exercise.review_status in PROTECTED:
                skipped += 1
                continue
            fields = {
                "category": entry["category"],
                "duration_minutes": entry["duration_minutes"],
                "pattern": entry["pattern"],
                "review_status": ReviewStatus.NEEDS_REVIEW,
            }
            if exercise is None:
                exercise = Exercise.objects.create(slug=entry["slug"], **fields)
                created += 1
            else:
                Exercise.objects.filter(pk=exercise.pk).update(**fields)
                updated += 1
            for language, text in entry["translations"].items():
                existing = ExerciseTranslation.objects.filter(
                    exercise=exercise, language=language
                ).first()
                if existing is not None and existing.review_status in PROTECTED:
                    continue
                ExerciseTranslation.objects.update_or_create(
                    exercise=exercise,
                    language=language,
                    defaults={**text, "review_status": ReviewStatus.NEEDS_REVIEW},
                )
        self.stdout.write(
            f"Exercises: {created} created, {updated} refreshed, {skipped} left untouched "
            "(already reviewed). All loaded content is NEEDS_HUMAN_REVIEW."
        )
