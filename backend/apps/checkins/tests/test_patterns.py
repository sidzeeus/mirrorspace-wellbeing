from __future__ import annotations

from datetime import timedelta

import pytest

from apps.checkins.dates import local_today
from apps.checkins.patterns import NOTE, OBSERVATION_TEMPLATES
from tests.factories import CheckInFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/patterns"

# Wording an observation must never use: causal, predictive, diagnostic, judging or
# advising language (non-negotiable 1, spec C.6 "Patterns").
BANNED_PHRASES = [
    "because",
    "cause",
    "leads to",
    "led to",
    "due to",
    "results in",
    "result of",
    "makes you",
    "made you",
    "affects",
    "impact",
    "will ",
    "predict",
    "likely",
    "risk",
    "warning",
    "diagnos",
    "disorder",
    "symptom",
    "depress",
    "anxi",
    "insomnia",
    "illness",
    "condition",
    "you are ",
    "you're ",
    "you have ",
    "should",
    "must",
    "need to",
    "try to",
    "better",
    "worse",
    "good",
    "bad",
    "healthy",
    "unhealthy",
    "normal",
    "streak",
    "missed",
    "only ",
    "score",
]


def seed(user, rows):
    """rows: (days_ago, sleep_hours, energy, mood, stress)."""
    today = local_today(user)
    for days_ago, sleep, energy, mood, stress in rows:
        CheckInFactory(
            user=user,
            local_date=today - timedelta(days=days_ago),
            sleep_hours=sleep,
            energy=energy,
            mood=mood,
            stress=stress,
        )


SHORT_SLEEP_LOW_ENERGY = [
    (1, 5, 2, 3, 3),
    (2, 5, 1, 3, 3),
    (3, 5.5, 2, 3, 3),
    (4, 8, 4, 3, 3),
    (5, 8, 5, 3, 3),
    (6, 8.5, 4, 3, 3),
    (7, 8, 4, 3, 3),
]


class TestObservationWording:
    @pytest.mark.parametrize("code", sorted(OBSERVATION_TEMPLATES))
    def test_no_template_uses_banned_wording(self, code):
        text = OBSERVATION_TEMPLATES[code].lower()
        used = [phrase for phrase in BANNED_PHRASES if phrase in text]
        assert used == [], f"observation '{code}' uses banned wording: {used}"

    def test_note_says_what_the_observations_are_not(self):
        assert "not a diagnosis" in NOTE

    def test_every_template_is_a_plain_sentence(self):
        for text in OBSERVATION_TEMPLATES.values():
            assert text[0].isupper() and text.endswith(".")
            assert "!" not in text


class TestPatterns:
    def test_requires_sign_in(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_empty_account_gets_a_calm_invitation(self, auth_client):
        body = auth_client.get(URL).json()
        assert body["check_in_days"] == 0
        assert body["series"] == [] and body["weekly"] == []
        assert [o["code"] for o in body["observations"]] == ["check_in_count", "not_enough_data"]
        assert body["note"] == NOTE

    def test_reports_a_visible_difference_as_an_observation_only(self, auth_client, user):
        seed(user, SHORT_SLEEP_LOW_ENERGY)
        body = auth_client.get(URL).json()
        codes = [o["code"] for o in body["observations"]]

        assert "sleep_energy_lower" in codes
        # Mood and stress were flat, so nothing is claimed about them.
        assert not any(c.startswith(("sleep_mood", "sleep_stress")) for c in codes)
        assert "not_enough_data" not in codes
        for observation in body["observations"]:
            assert observation["text"] == OBSERVATION_TEMPLATES[observation["code"]].format(
                **observation["params"]
            )

    def test_says_nothing_when_there_are_too_few_days(self, auth_client, user):
        seed(user, SHORT_SLEEP_LOW_ENERGY[:4])
        codes = [o["code"] for o in auth_client.get(URL).json()["observations"]]
        assert codes == ["check_in_count", "not_enough_data"]

    def test_says_nothing_when_the_difference_is_small(self, auth_client, user):
        seed(user, [(i, 5 if i % 2 else 8, 3, 3, 3) for i in range(1, 9)])
        codes = [o["code"] for o in auth_client.get(URL).json()["observations"]]
        assert codes == ["check_in_count", "not_enough_data"]

    def test_series_and_weekly_averages(self, auth_client, user):
        seed(user, SHORT_SLEEP_LOW_ENERGY)
        body = auth_client.get(URL).json()

        assert body["check_in_days"] == 7
        assert len(body["series"]) == 7
        assert body["series"] == sorted(body["series"], key=lambda r: r["local_date"])
        assert sum(week["check_ins"] for week in body["weekly"]) == 7
        assert set(body["weekly"][0]) == {
            "week_start",
            "check_ins",
            "average_mood",
            "average_sleep_hours",
            "average_sleep_quality",
            "average_energy",
            "average_stress",
        }
        assert all(week["average_mood"] == 3 for week in body["weekly"])

    def test_uses_only_the_signed_in_users_data(self, auth_client, user, other_user):
        seed(other_user, SHORT_SLEEP_LOW_ENERGY)
        body = auth_client.get(URL).json()
        assert body["check_in_days"] == 0
        assert body["series"] == []
        assert "sleep_energy_lower" not in [o["code"] for o in body["observations"]]

    @pytest.mark.parametrize(
        ("query", "expected"),
        [("", 28), ("?days=7", 7), ("?days=1", 7), ("?days=9999", 90), ("?days=abc", 28)],
    )
    def test_period_is_clamped(self, auth_client, query, expected):
        assert auth_client.get(URL + query).json()["range"]["days"] == expected

    def test_check_ins_outside_the_period_are_left_out(self, auth_client, user):
        seed(user, [(40, 7, 3, 3, 3), (2, 7, 3, 3, 3)])
        assert auth_client.get(f"{URL}?days=28").json()["check_in_days"] == 1
