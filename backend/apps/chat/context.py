"""What Sushi may know about the student, when they choose to share it (decision B83).

Off by default. When the student turns it on (`ChatContextSetting`), the AI is given a
short plain-text summary built here, and nothing else from their records:

- check-ins and sleep from the last 14 days (counts and averages, plus the latest)
- their active trigger words
- episodes from the last 14 days (when, how intense, which trigger, what helped)
- the warning signs and coping steps from their safety plan

Never included: the people named in the safety plan (other people's details), Vent
entries, trusted contacts, name, email or anything else.

`match_triggers` is code, not AI: if a message mentions one of the student's own
active triggers, the reply carries their coping steps, whatever the model does. It
shows the student their own plan. It contacts nobody.

Nothing here logs anything.
"""

from __future__ import annotations

import re
from datetime import timedelta
from statistics import mean
from typing import Any

from django.utils import timezone

from apps.accounts.models import User
from apps.checkins.dates import local_today
from apps.checkins.models import CheckIn
from apps.episodes.models import Episode, Trigger
from apps.safety.models import SafetyPlan

from .models import ChatContextSetting

DAYS = 14


def is_enabled(user: User) -> bool:
    return ChatContextSetting.objects.filter(user=user, enabled=True).exists()


def _average(values: list[Any]) -> str | None:
    numbers = [float(value) for value in values if value is not None]
    return f"{mean(numbers):.1f}" if numbers else None


def build_context(user: User) -> str:
    """The exact text the AI receives. Shown to the student as the preview."""
    today = local_today(user)
    since = today - timedelta(days=DAYS - 1)
    lines: list[str] = []

    check_ins = list(
        CheckIn.objects.filter(user=user, local_date__gte=since).order_by("-local_date")
    )
    lines.append(f"Check-ins in the last {DAYS} days: {len(check_ins)}")
    if check_ins:
        for label, field, unit in (
            ("mood", "mood", " out of 5"),
            ("energy", "energy", " out of 5"),
            ("stress", "stress", " out of 5"),
            ("sleep", "sleep_hours", " hours a night"),
        ):
            average = _average([getattr(row, field) for row in check_ins])
            if average:
                lines.append(f"- Average {label}: {average}{unit}")
        latest = check_ins[0]
        parts = [
            f"{name} {value}"
            for name, value in (
                ("mood", latest.mood),
                (
                    "sleep",
                    f"{latest.sleep_hours} hours" if latest.sleep_hours is not None else None,
                ),
                ("energy", latest.energy),
                ("stress", latest.stress),
            )
            if value is not None
        ]
        lines.append(f"- Latest check-in ({latest.local_date.isoformat()}): {', '.join(parts)}")

    triggers = [trigger.label for trigger in Trigger.objects.filter(user=user, is_active=True)]
    if triggers:
        lines.append("Their trigger list: " + "; ".join(triggers))

    episodes = Episode.objects.filter(
        user=user, occurred_at__gte=timezone.now() - timedelta(days=DAYS)
    ).select_related("trigger")
    episode_lines = []
    for episode in episodes[:5]:
        day = timezone.localtime(episode.occurred_at).date().isoformat()
        detail = f"- {day}, intensity {episode.intensity} of 5"
        if episode.trigger is not None:
            detail += f", trigger: {episode.trigger.label}"
        if episode.what_helped:
            detail += f", what helped: {episode.what_helped}"
        episode_lines.append(detail)
    if episode_lines:
        lines.append(f"Hard moments they logged in the last {DAYS} days:")
        lines.extend(episode_lines)

    plan = SafetyPlan.objects.filter(user=user).first()
    if plan and plan.warning_signs:
        lines.append("Warning signs from their safety plan: " + "; ".join(plan.warning_signs))
    if plan and plan.coping_steps:
        lines.append("Coping steps from their safety plan: " + "; ".join(plan.coping_steps))
    return "\n".join(lines)


def _words(text: str) -> str:
    return " " + re.sub(r"[^\w]+", " ", text.lower()).strip() + " "


def match_triggers(user: User, text: str) -> list[str]:
    """The student's own active triggers that appear in what they just wrote."""
    said = _words(text)
    return [
        trigger.label
        for trigger in Trigger.objects.filter(user=user, is_active=True)
        if _words(trigger.label).strip() and _words(trigger.label) in said
    ]


def plan_suggestion(user: User, matched: list[str]) -> dict[str, Any] | None:
    """Their own coping steps, to show beside the reply when a trigger came up."""
    if not matched:
        return None
    plan = SafetyPlan.objects.filter(user=user).first()
    return {
        "matched": matched,
        "coping_steps": list(plan.coping_steps) if plan else [],
        "href": "/plan",
    }
