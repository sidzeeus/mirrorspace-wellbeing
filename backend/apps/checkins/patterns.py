"""Simple, descriptive summaries of a person's own check-ins.

NEEDS_HUMAN_REVIEW (docs/review-needed.md R10): the wording below is a placeholder.

Rules for anything added here:
- Describe what was entered. Never diagnose, predict, advise, or say one thing causes
  another. `tests` scan every template for banned wording.
- No scores, grades, streaks or "better/worse" judgements about the person.
- An observation is only shown when there is enough data and a visible difference.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean, median
from typing import Any

from apps.accounts.models import User

from .dates import local_today
from .models import METRIC_FIELDS, CheckIn

DEFAULT_DAYS = 28
MIN_DAYS, MAX_DAYS = 7, 90

# Both values must be present on at least this many days before a comparison is shown.
MIN_PAIRED_DAYS = 6
# ...and at least this many days must fall on each side of the person's usual sleep.
MIN_GROUP_DAYS = 2
# Smallest difference between the two averages (on the 1 to 5 scale) worth mentioning.
MIN_DIFFERENCE = 0.5

NOTE = (
    "These observations come only from what you entered. They are not a diagnosis, "
    "and they cannot show that one thing leads to another."
)

OBSERVATION_TEMPLATES: dict[str, str] = {
    "check_in_count": "You checked in on {count} of the last {days} days.",
    "not_enough_data": ("Patterns appear here after about a week of check-ins. There is no rush."),
    "sleep_energy_lower": (
        "On days you logged less sleep than your usual, you rated your energy lower on average."
    ),
    "sleep_energy_higher": (
        "On days you logged less sleep than your usual, you rated your energy higher on average."
    ),
    "sleep_mood_lower": (
        "On days you logged less sleep than your usual, you rated your mood lower on average."
    ),
    "sleep_mood_higher": (
        "On days you logged less sleep than your usual, you rated your mood higher on average."
    ),
    "sleep_stress_lower": (
        "On days you logged less sleep than your usual, you rated your stress lower on average."
    ),
    "sleep_stress_higher": (
        "On days you logged less sleep than your usual, you rated your stress higher on average."
    ),
}


def clamp_days(raw: str | None) -> int:
    try:
        days = int(raw) if raw is not None else DEFAULT_DAYS
    except ValueError:
        days = DEFAULT_DAYS
    return max(MIN_DAYS, min(MAX_DAYS, days))


def _observation(code: str, **params: Any) -> dict[str, Any]:
    return {"code": code, "text": OBSERVATION_TEMPLATES[code].format(**params), "params": params}


def _average(values: list[float]) -> float | None:
    return round(fmean(values), 2) if values else None


def _sleep_comparison(rows: list[CheckIn], metric: str) -> dict[str, Any] | None:
    """Compare a rating on shorter-sleep days with the person's other days."""
    pairs = [
        (float(row.sleep_hours), float(getattr(row, metric)))
        for row in rows
        if row.sleep_hours is not None and getattr(row, metric) is not None
    ]
    if len(pairs) < MIN_PAIRED_DAYS:
        return None
    usual = median(hours for hours, _ in pairs)
    shorter = [value for hours, value in pairs if hours < usual]
    other = [value for hours, value in pairs if hours >= usual]
    if len(shorter) < MIN_GROUP_DAYS or len(other) < MIN_GROUP_DAYS:
        return None
    difference = fmean(shorter) - fmean(other)
    if abs(difference) < MIN_DIFFERENCE:
        return None
    direction = "lower" if difference < 0 else "higher"
    return _observation(f"sleep_{metric}_{direction}")


def _weekly(rows: list[CheckIn]) -> list[dict[str, Any]]:
    weeks: dict[date, list[CheckIn]] = defaultdict(list)
    for row in rows:
        weeks[row.local_date - timedelta(days=row.local_date.weekday())].append(row)
    summary = []
    for week_start in sorted(weeks):
        entries = weeks[week_start]
        item: dict[str, Any] = {"week_start": week_start.isoformat(), "check_ins": len(entries)}
        for metric in METRIC_FIELDS:
            item[f"average_{metric}"] = _average(
                [float(getattr(e, metric)) for e in entries if getattr(e, metric) is not None]
            )
        summary.append(item)
    return summary


def build_patterns(user: User, days: int) -> dict[str, Any]:
    end = local_today(user)
    start = end - timedelta(days=days - 1)
    rows = list(
        CheckIn.objects.filter(user=user, local_date__gte=start, local_date__lte=end).order_by(
            "local_date"
        )
    )

    observations = [_observation("check_in_count", count=len(rows), days=days)]
    comparisons = [
        found
        for metric in ("energy", "mood", "stress")
        if (found := _sleep_comparison(rows, metric)) is not None
    ]
    observations.extend(comparisons)
    if not comparisons:
        observations.append(_observation("not_enough_data"))

    return {
        "range": {"from": start.isoformat(), "to": end.isoformat(), "days": days},
        "check_in_days": len(rows),
        "series": [
            {
                "local_date": row.local_date.isoformat(),
                **{
                    metric: (
                        float(getattr(row, metric)) if getattr(row, metric) is not None else None
                    )
                    for metric in METRIC_FIELDS
                },
            }
            for row in rows
        ],
        "weekly": _weekly(rows),
        "observations": observations,
        "note": NOTE,
    }
