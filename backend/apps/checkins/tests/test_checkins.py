from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction

from apps.checkins.dates import BACKFILL_DAYS, local_today
from apps.checkins.models import CheckIn
from tests.factories import CheckInFactory, UserFactory
from tests.harness import OwnedResourceContract

pytestmark = pytest.mark.django_db

URL = "/api/v1/check-ins"


class TestCheckInIsolation(OwnedResourceContract):
    list_url = URL
    update_payload = {"mood": 1}

    def make(self, user):
        return CheckInFactory(user=user)


class TestCreate:
    def test_saves_structured_values_for_today(self, auth_client, user):
        response = auth_client.post(
            URL,
            {"mood": 4, "sleep_hours": "7.5", "sleep_quality": 3, "energy": 2, "stress": 5},
            format="json",
        )
        assert response.status_code == 201
        row = CheckIn.objects.get(user=user)
        assert (row.mood, float(row.sleep_hours), row.sleep_quality, row.energy, row.stress) == (
            4,
            7.5,
            3,
            2,
            5,
        )
        assert row.local_date == local_today(user)
        assert row.timezone == "Asia/Kolkata"

    def test_every_value_is_optional_but_one_is_needed(self, auth_client):
        assert auth_client.post(URL, {"mood": 2}, format="json").status_code == 201
        empty = auth_client.post(URL, {}, format="json")
        assert empty.status_code == 400
        assert "at least one value" in str(empty.json())

    def test_skipping_stores_nothing(self, auth_client, user):
        auth_client.post(URL, {"mood": None, "energy": None}, format="json")
        assert not CheckIn.objects.filter(user=user).exists()

    def test_second_post_on_the_same_day_replaces_the_first(self, auth_client, user):
        first = auth_client.post(URL, {"mood": 2, "energy": 4}, format="json")
        second = auth_client.post(URL, {"mood": 5}, format="json")

        assert (first.status_code, second.status_code) == (201, 200)
        assert first.json()["id"] == second.json()["id"]
        row = CheckIn.objects.get(user=user)
        assert row.mood == 5
        assert row.energy is None

    @pytest.mark.parametrize(
        "payload",
        [
            {"mood": 0},
            {"mood": 6},
            {"stress": -1},
            {"energy": "high"},
            {"sleep_quality": 9},
            {"sleep_hours": "24.5"},
            {"sleep_hours": "-1"},
            {"sleep_hours": "7.25"},
        ],
    )
    def test_rejects_out_of_range_values(self, auth_client, user, payload):
        response = auth_client.post(URL, payload, format="json")
        assert response.status_code == 400
        assert set(response.json()) == set(payload)
        assert not CheckIn.objects.filter(user=user).exists()

    def test_owner_comes_from_the_session_not_the_body(self, auth_client, user, other_user):
        response = auth_client.post(
            URL,
            {"mood": 3, "user": str(other_user.pk), "user_id": str(other_user.pk)},
            format="json",
        )
        assert response.status_code == 201
        assert CheckIn.objects.get().user_id == user.pk
        assert "user" not in response.json()

    def test_there_is_no_free_text_note(self, auth_client, user):
        """Decision D4: structured fields only."""
        response = auth_client.post(URL, {"mood": 3, "note": "private words"}, format="json")
        assert response.status_code == 201
        assert "note" not in response.json()
        text_fields = [
            f.name
            for f in CheckIn._meta.get_fields()
            if f.get_internal_type() in ("TextField", "CharField") and f.name != "timezone"
        ]
        assert text_fields == []

    def test_requires_sign_in(self, api_client):
        assert api_client.post(URL, {"mood": 3}, format="json").status_code == 401


class TestLocalDate:
    """The check-in belongs to the day the person was living in, not the UTC day."""

    @pytest.mark.parametrize(
        ("zone", "utc_moment", "expected"),
        [
            # Late evening UTC is already tomorrow in India.
            ("Asia/Kolkata", datetime(2026, 5, 10, 19, 0, tzinfo=UTC), date(2026, 5, 11)),
            ("Asia/Kolkata", datetime(2026, 5, 10, 18, 29, tzinfo=UTC), date(2026, 5, 10)),
            # Early morning UTC is still yesterday in New York.
            ("America/New_York", datetime(2026, 1, 15, 3, 30, tzinfo=UTC), date(2026, 1, 14)),
            # After the clocks go forward (8 March 2026) New York is UTC-4, so 04:30 UTC
            # is past midnight. A fixed UTC-5 offset would wrongly say 8 March.
            ("America/New_York", datetime(2026, 3, 9, 4, 30, tzinfo=UTC), date(2026, 3, 9)),
            ("America/New_York", datetime(2026, 3, 9, 3, 59, tzinfo=UTC), date(2026, 3, 8)),
            # The far side of the date line.
            ("Pacific/Kiritimati", datetime(2026, 5, 10, 10, 30, tzinfo=UTC), date(2026, 5, 11)),
        ],
    )
    def test_date_follows_the_users_time_zone(self, set_now, as_user, zone, utc_moment, expected):
        user = UserFactory(timezone=zone)
        set_now(utc_moment)

        response = as_user(user).post(URL, {"mood": 3}, format="json")

        assert response.status_code == 201
        assert response.json()["local_date"] == expected.isoformat()
        assert response.json()["timezone"] == zone

    def test_same_instant_is_a_different_day_for_two_people(self, set_now, as_user):
        india, new_york = (
            UserFactory(timezone="Asia/Kolkata"),
            UserFactory(timezone="America/New_York"),
        )
        set_now(datetime(2026, 5, 10, 20, 0, tzinfo=UTC))
        assert as_user(india).post(URL, {"mood": 3}, format="json").json()["local_date"] == (
            "2026-05-11"
        )
        assert as_user(new_york).post(URL, {"mood": 3}, format="json").json()["local_date"] == (
            "2026-05-10"
        )

    def test_changing_time_zone_does_not_rewrite_past_check_ins(self, auth_client, user):
        first = auth_client.post(URL, {"mood": 3}, format="json").json()
        auth_client.patch("/api/v1/auth/me", {"timezone": "Europe/London"}, format="json")
        row = CheckIn.objects.get(pk=first["id"])
        assert row.timezone == "Asia/Kolkata"
        assert row.local_date.isoformat() == first["local_date"]

    def test_can_backfill_recent_days_only(self, set_now, as_user, user):
        set_now(datetime(2026, 5, 10, 6, 0, tzinfo=UTC))
        client = as_user(user)
        today = date(2026, 5, 10)

        yesterday = client.post(
            URL, {"mood": 2, "local_date": str(today - timedelta(days=1))}, format="json"
        )
        oldest = client.post(
            URL,
            {"mood": 2, "local_date": str(today - timedelta(days=BACKFILL_DAYS))},
            format="json",
        )
        too_old = client.post(
            URL,
            {"mood": 2, "local_date": str(today - timedelta(days=BACKFILL_DAYS + 1))},
            format="json",
        )
        future = client.post(
            URL, {"mood": 2, "local_date": str(today + timedelta(days=1))}, format="json"
        )

        assert (yesterday.status_code, oldest.status_code) == (201, 201)
        assert too_old.status_code == future.status_code == 400
        assert "local_date" in too_old.json() and "local_date" in future.json()

    def test_date_cannot_be_changed_afterwards(self, auth_client, user):
        created = auth_client.post(URL, {"mood": 3}, format="json").json()
        response = auth_client.patch(
            f"{URL}/{created['id']}", {"local_date": "2020-01-01"}, format="json"
        )
        assert response.status_code == 400


class TestUpdateAndDelete:
    def test_owner_can_change_and_delete(self, auth_client, user):
        row = CheckInFactory(user=user, mood=2)
        patched = auth_client.patch(f"{URL}/{row.pk}", {"mood": 4, "stress": 1}, format="json")
        assert patched.status_code == 200
        row.refresh_from_db()
        assert (row.mood, row.stress) == (4, 1)

        assert auth_client.delete(f"{URL}/{row.pk}").status_code == 204
        assert not CheckIn.objects.filter(pk=row.pk).exists()

    def test_cannot_blank_every_value(self, auth_client, user):
        row = CheckInFactory(user=user, mood=2)
        response = auth_client.patch(f"{URL}/{row.pk}", {"mood": None}, format="json")
        assert response.status_code == 400
        row.refresh_from_db()
        assert row.mood == 2


class TestList:
    def test_is_paginated_newest_first(self, auth_client, user):
        CheckInFactory.create_batch(25, user=user)
        body = auth_client.get(URL).json()

        assert body["count"] == 25
        assert len(body["results"]) == 20
        assert body["next"] is not None
        dates = [row["local_date"] for row in body["results"]]
        assert dates == sorted(dates, reverse=True)
        assert len(auth_client.get(f"{URL}?page=2").json()["results"]) == 5

    def test_page_size_is_capped(self, auth_client, user):
        CheckInFactory.create_batch(3, user=user)
        assert len(auth_client.get(f"{URL}?page_size=2").json()["results"]) == 2
        assert auth_client.get(f"{URL}?page_size=100000").status_code == 200

    def test_can_filter_by_date_range(self, auth_client, user):
        for day in (1, 10, 20):
            CheckInFactory(user=user, local_date=date(2026, 2, day))
        body = auth_client.get(f"{URL}?from=2026-02-05&to=2026-02-15").json()
        assert [row["local_date"] for row in body["results"]] == ["2026-02-10"]

    def test_bad_filter_values_are_ignored_not_fatal(self, auth_client, user):
        CheckInFactory(user=user)
        assert auth_client.get(f"{URL}?from=not-a-date").json()["count"] == 1

    def test_response_has_only_the_expected_fields(self, auth_client, user):
        CheckInFactory(user=user)
        row = auth_client.get(URL).json()["results"][0]
        assert set(row) == {
            "id",
            "local_date",
            "timezone",
            "mood",
            "sleep_hours",
            "sleep_quality",
            "energy",
            "stress",
            "created_at",
            "updated_at",
        }


class TestDatabaseConstraints:
    """The database refuses bad rows even if a code path skips the serializer."""

    def _expect_rejected(self, **fields):
        with pytest.raises(IntegrityError), transaction.atomic():
            CheckIn.objects.create(timezone="UTC", **fields)

    def test_one_check_in_per_user_per_day(self, user):
        CheckInFactory(user=user, local_date=date(2026, 3, 1))
        self._expect_rejected(user=user, local_date=date(2026, 3, 1), mood=3)

    def test_two_users_can_check_in_on_the_same_day(self, user, other_user):
        CheckInFactory(user=user, local_date=date(2026, 3, 1))
        CheckInFactory(user=other_user, local_date=date(2026, 3, 1))
        assert CheckIn.objects.count() == 2

    @pytest.mark.parametrize(
        "fields",
        [{"mood": 6}, {"energy": 0}, {"stress": 9}, {"sleep_quality": 0}, {"sleep_hours": 30}],
    )
    def test_values_must_be_in_range(self, user, fields):
        self._expect_rejected(user=user, local_date=date(2026, 3, 2), **fields)

    def test_an_empty_check_in_cannot_be_stored(self, user):
        self._expect_rejected(user=user, local_date=date(2026, 3, 3))

    def test_user_and_date_index_exists(self):
        index_fields = [tuple(index.fields) for index in CheckIn._meta.indexes]
        assert ("user", "-local_date") in index_fields
