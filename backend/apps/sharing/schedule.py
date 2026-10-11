"""When the next weekly note is due.

The student picks a weekday and an hour in their own time zone. The stored
`next_send_at` is that wall-clock time converted to UTC with the zone database, so
the note keeps arriving at the same local hour when the clocks change.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

DEFAULT_WEEKDAY = 0  # Monday
DEFAULT_HOUR = 9


def next_send_at(after: datetime, zone: ZoneInfo, weekday: int, hour: int) -> datetime:
    """The first `weekday` at `hour`:00 local time that is strictly after `after`."""
    local = after.astimezone(zone)
    days_ahead = (weekday - local.weekday()) % 7
    for extra_weeks in (0, 1):
        day = local.date() + timedelta(days=days_ahead + 7 * extra_weeks)
        # Building the local time and converting to UTC handles daylight saving. An
        # hour skipped by the clock change resolves to the instant just after the gap.
        candidate = datetime.combine(day, time(hour), tzinfo=zone).astimezone(UTC)
        if candidate > after:
            return candidate
    raise AssertionError("unreachable: one of two consecutive weeks is always in the future")
