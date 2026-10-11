"""The weekly note to a trusted contact (decision D3).

The note may contain exactly four things: the student's display name, the week
covered, "checked in X of 7 days", and one fixed neutral line. Nothing else.

That limit is enforced by structure, not by care:

- `WeeklyFields` is the only thing the renderer accepts, and it has exactly the
  allowed fields. There is nowhere to put a mood value, a trigger or a note.
- `collect_weekly_fields` runs one COUNT query on check-in dates. It never loads a
  check-in's values or any other model.
- Tests fail if a field is added to `WeeklyFields`, or if any other data about the
  student appears in a rendered note.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.accounts.models import Profile, User
from apps.checkins.models import CheckIn

from .notices import WEEKLY_NEUTRAL_LINE, WEEKLY_NOTICE_VERSION

DAYS_IN_WEEK = 7


@dataclass(frozen=True)
class WeeklyFields:
    display_name: str
    week_start: date
    week_end: date
    check_in_days: int


# The complete list of what a weekly note may carry. A test pins this.
ALLOWED_FIELDS = ("display_name", "week_start", "week_end", "check_in_days")
assert tuple(f.name for f in fields(WeeklyFields)) == ALLOWED_FIELDS  # noqa: S101


@dataclass(frozen=True)
class RenderedMessage:
    subject: str
    body: str


def covered_week(send_moment: datetime, zone: ZoneInfo) -> tuple[date, date]:
    """The seven full local days that ended the day before the note is sent."""
    week_end = send_moment.astimezone(zone).date() - timedelta(days=1)
    return week_end - timedelta(days=DAYS_IN_WEEK - 1), week_end


def collect_weekly_fields(user: User, week_start: date, week_end: date) -> WeeklyFields:
    display_name = Profile.objects.filter(user=user).values_list("display_name", flat=True).first()
    check_in_days = CheckIn.objects.filter(
        user=user, local_date__gte=week_start, local_date__lte=week_end
    ).count()
    return WeeklyFields(
        display_name=display_name or "",
        week_start=week_start,
        week_end=week_end,
        check_in_days=min(check_in_days, DAYS_IN_WEEK),
    )


def _format_date(value: date) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


WEEKLY_SUBJECT = "Weekly note from {display_name}"
WEEKLY_BODY = (
    "{display_name} uses {app_name} and chose to send you this short note each week.\n"
    "\n"
    "Week of {week_start} to {week_end}: checked in {check_in_days} of 7 days.\n"
    "\n"
    "{neutral_line}\n"
    "\n"
    "{app_name} is a self-help tool. It is not monitored by anyone and it is not an "
    "emergency service."
)


def render_weekly(values: WeeklyFields) -> RenderedMessage:
    """Pure function of the allowed fields and fixed text. It cannot query anything."""
    params = {
        "display_name": values.display_name,
        "week_start": _format_date(values.week_start),
        "week_end": _format_date(values.week_end),
        "check_in_days": values.check_in_days,
        "neutral_line": WEEKLY_NEUTRAL_LINE,
        "app_name": settings.APP_NAME,
    }
    return RenderedMessage(
        subject=WEEKLY_SUBJECT.format(**params), body=WEEKLY_BODY.format(**params)
    )


def weekly_format_hash() -> str:
    """Fingerprint of the note's wording and notice version.

    The student's confirmation must quote this, which proves they were shown the
    current wording. It does not depend on that week's numbers.
    """
    material = "\n".join(
        [WEEKLY_NOTICE_VERSION, WEEKLY_SUBJECT, WEEKLY_BODY, WEEKLY_NEUTRAL_LINE, *ALLOWED_FIELDS]
    )
    return hashlib.sha256(material.encode()).hexdigest()
