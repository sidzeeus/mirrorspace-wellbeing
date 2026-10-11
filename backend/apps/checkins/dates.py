"""Working out "today" for a person, in their own time zone.

Timestamps are stored in UTC. A check-in belongs to the calendar day the person was
living in when they made it, which depends on their zone and on daylight-saving time,
so the date is always derived with the zone database rather than a fixed offset.
"""

from __future__ import annotations

import zoneinfo
from datetime import date, datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Profile, User

# How far back a check-in can be added or moved, in days.
BACKFILL_DAYS = 7


def user_zone(user: User) -> zoneinfo.ZoneInfo:
    name = (
        Profile.objects.filter(user=user).values_list("timezone", flat=True).first()
        or settings.DEFAULT_USER_TIMEZONE
    )
    try:
        return zoneinfo.ZoneInfo(name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return zoneinfo.ZoneInfo(settings.DEFAULT_USER_TIMEZONE)


def local_date_at(moment: datetime, zone: zoneinfo.ZoneInfo) -> date:
    return moment.astimezone(zone).date()


def local_today(user: User) -> date:
    return local_date_at(timezone.now(), user_zone(user))


def earliest_allowed(today: date) -> date:
    return today - timedelta(days=BACKFILL_DAYS)
