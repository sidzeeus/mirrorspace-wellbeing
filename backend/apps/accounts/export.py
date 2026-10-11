"""Data export: everything the app holds about one student, as JSON.

Each app registers a section here from its `AppConfig.ready()`. A test
(`tests/test_data_coverage.py`) fails if any model with a link to the user is not
covered by a registered section, so new data cannot be added without also being
exportable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import models
from django.utils import timezone

from .models import Profile, User

FORMAT_VERSION = 1


@dataclass(frozen=True)
class ExportSection:
    key: str
    models: tuple[type[models.Model], ...]
    build: Callable[[User], Any]


_sections: dict[str, ExportSection] = {}


def register_export(
    key: str, covered_models: tuple[type[models.Model], ...], build: Callable[[User], Any]
) -> None:
    _sections[key] = ExportSection(key, covered_models, build)


def covered_models() -> set[type[models.Model]]:
    return {model for section in _sections.values() for model in section.models}


def build_export(user: User) -> dict[str, Any]:
    data: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "exported_at": timezone.now().isoformat(),
    }
    for key in sorted(_sections):
        data[key] = _sections[key].build(user)
    return data


def _account_section(user: User) -> dict[str, Any]:
    profile = Profile.objects.get(user=user)
    return {
        "id": str(user.pk),
        "email": user.email,
        "preferred_language": user.preferred_language,
        "display_name": profile.display_name,
        "timezone": profile.timezone,
        "created_at": user.created_at.isoformat(),
        "email_verified_at": _iso(user.email_verified_at),
        "age_confirmed_at": _iso(user.age_confirmed_at),
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


register_export("account", (User, Profile), _account_section)
