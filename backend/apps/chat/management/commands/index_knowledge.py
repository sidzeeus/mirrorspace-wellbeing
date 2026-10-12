"""Rebuild the chat's search index:  python manage.py index_knowledge

Only documents a reviewer has approved are indexed. (In development, with
SHOW_UNREVIEWED_CONTENT on, placeholders waiting for review are indexed too so the
chat can be tried; production forces that switch off.) Documents that are not
approved have their passages removed, so they can no longer be quoted.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.chat.knowledge import index_all


class Command(BaseCommand):
    help = "Chunk and embed approved knowledge documents for retrieval."

    def handle(self, *args: Any, **options: Any) -> None:
        result = index_all()
        self.stdout.write(
            f"Indexed {result['documents_indexed']} document(s) into {result['passages']} "
            f"passage(s). Skipped {result['documents_skipped']} that are not approved."
        )
