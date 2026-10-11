from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.episodes.models import Episode, Trigger
from apps.episodes.serializers import MAX_TRIGGERS
from tests.factories import EpisodeFactory, ExerciseFactory, TriggerFactory
from tests.harness import OwnedResourceContract, client_for

pytestmark = pytest.mark.django_db

TRIGGERS = "/api/v1/triggers"
EPISODES = "/api/v1/episodes"

CANARY = "CANARY-private-trigger-words"


def raw_column(table: str, column: str, pk) -> str:
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT "{column}" FROM "{table}" WHERE id = %s', [pk])  # noqa: S608
        return cursor.fetchone()[0]


class TestTriggerIsolation(OwnedResourceContract):
    list_url = TRIGGERS
    update_payload = {"label": "changed by intruder"}

    def make(self, user):
        return TriggerFactory(user=user)


class TestEpisodeIsolation(OwnedResourceContract):
    list_url = EPISODES
    update_payload = {"intensity": 1}

    def make(self, user):
        return EpisodeFactory(user=user)


class TestTriggers:
    def test_create_list_archive(self, auth_client, user):
        created = auth_client.post(TRIGGERS, {"label": "Exam week"}, format="json")
        assert created.status_code == 201
        assert created.json()["is_active"] is True
        trigger_id = created.json()["id"]

        archived = auth_client.patch(
            f"{TRIGGERS}/{trigger_id}", {"is_active": False}, format="json"
        )
        assert archived.status_code == 200
        assert auth_client.get(TRIGGERS).json()["count"] == 0
        with_archived = auth_client.get(f"{TRIGGERS}?include_archived=true").json()
        assert [t["id"] for t in with_archived["results"]] == [trigger_id]
        assert Trigger.objects.filter(pk=trigger_id).exists()

    def test_label_is_encrypted_in_the_database(self, auth_client):
        trigger_id = auth_client.post(TRIGGERS, {"label": CANARY}, format="json").json()["id"]
        stored = raw_column("episodes_trigger", "label", trigger_id)
        assert CANARY not in stored
        assert stored.startswith("gAAAA")
        assert auth_client.get(f"{TRIGGERS}/{trigger_id}").json()["label"] == CANARY

    def test_label_is_required_trimmed_and_limited(self, auth_client):
        assert auth_client.post(TRIGGERS, {"label": "   "}, format="json").status_code == 400
        assert auth_client.post(TRIGGERS, {"label": "x" * 81}, format="json").status_code == 400
        ok = auth_client.post(TRIGGERS, {"label": "  Deadlines  "}, format="json")
        assert ok.json()["label"] == "Deadlines"

    def test_duplicate_label_is_rejected_for_the_same_person_only(self, auth_client, other_user):
        auth_client.post(TRIGGERS, {"label": "Deadlines"}, format="json")
        duplicate = auth_client.post(TRIGGERS, {"label": "deadlines"}, format="json")
        assert duplicate.status_code == 400
        assert "label" in duplicate.json()
        assert (
            client_for(other_user).post(TRIGGERS, {"label": "Deadlines"}, format="json").status_code
            == 201
        )

    def test_renaming_to_its_own_name_is_allowed(self, auth_client, user):
        trigger = TriggerFactory(user=user, label="Deadlines")
        response = auth_client.patch(
            f"{TRIGGERS}/{trigger.pk}", {"label": "Deadlines"}, format="json"
        )
        assert response.status_code == 200

    def test_preferred_exercises_must_be_reviewed_content(self, auth_client, user):
        approved = ExerciseFactory()
        unreviewed = ExerciseFactory(review_status="needs_review")
        trigger = TriggerFactory(user=user)

        ok = auth_client.patch(
            f"{TRIGGERS}/{trigger.pk}",
            {"preferred_exercise_ids": [str(approved.pk)]},
            format="json",
        )
        bad = auth_client.patch(
            f"{TRIGGERS}/{trigger.pk}",
            {"preferred_exercise_ids": [str(unreviewed.pk)]},
            format="json",
        )

        assert ok.status_code == 200
        assert ok.json()["preferred_exercise_ids"] == [str(approved.pk)]
        assert bad.status_code == 400

    def test_number_of_triggers_is_limited(self, auth_client, user):
        TriggerFactory.create_batch(MAX_TRIGGERS, user=user)
        response = auth_client.post(TRIGGERS, {"label": "one more"}, format="json")
        assert response.status_code == 400

    def test_owner_comes_from_the_session(self, auth_client, user, other_user):
        auth_client.post(TRIGGERS, {"label": "Mine", "user": str(other_user.pk)}, format="json")
        assert Trigger.objects.get().user_id == user.pk

    def test_response_fields(self, auth_client, user):
        TriggerFactory(user=user)
        assert set(auth_client.get(TRIGGERS).json()["results"][0]) == {
            "id",
            "label",
            "is_active",
            "preferred_exercise_ids",
            "created_at",
        }


class TestEpisodes:
    def payload(self, **overrides):
        data = {"occurred_at": (timezone.now() - timedelta(minutes=30)).isoformat(), "intensity": 4}
        data.update(overrides)
        return data

    def test_quick_log_needs_only_time_and_intensity(self, auth_client, user):
        response = auth_client.post(EPISODES, self.payload(), format="json")
        assert response.status_code == 201
        episode = Episode.objects.get(user=user)
        assert episode.intensity == 4
        assert episode.trigger is None and episode.what_helped == ""

    def test_full_log(self, auth_client, user):
        trigger, exercise = TriggerFactory(user=user), ExerciseFactory()
        response = auth_client.post(
            EPISODES,
            self.payload(
                duration_minutes=20,
                trigger=str(trigger.pk),
                helped_exercise=str(exercise.pk),
                what_helped="Calling my sister",
            ),
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["trigger"] == str(trigger.pk)
        assert body["helped_exercise"] == str(exercise.pk)
        assert body["what_helped"] == "Calling my sister"

    def test_cannot_attach_another_persons_trigger(self, auth_client, user, other_user):
        foreign = TriggerFactory(user=other_user)
        made_up = "00000000-0000-4000-8000-000000000000"

        attempt = auth_client.post(EPISODES, self.payload(trigger=str(foreign.pk)), format="json")
        unknown = auth_client.post(EPISODES, self.payload(trigger=made_up), format="json")

        assert attempt.status_code == unknown.status_code == 400
        # Same shape of error as an id that does not exist: no hint that it is real.
        assert set(attempt.json()) == set(unknown.json()) == {"trigger"}
        assert not Episode.objects.exists()

    def test_cannot_move_an_episode_onto_another_persons_trigger(
        self, auth_client, user, other_user
    ):
        episode = EpisodeFactory(user=user)
        foreign = TriggerFactory(user=other_user)
        response = auth_client.patch(
            f"{EPISODES}/{episode.pk}", {"trigger": str(foreign.pk)}, format="json"
        )
        assert response.status_code == 400
        episode.refresh_from_db()
        assert episode.trigger is None

    def test_what_helped_is_encrypted_in_the_database(self, auth_client):
        episode_id = auth_client.post(
            EPISODES, self.payload(what_helped=CANARY), format="json"
        ).json()["id"]
        stored = raw_column("episodes_episode", "what_helped", episode_id)
        assert CANARY not in stored and stored.startswith("gAAAA")

    @pytest.mark.parametrize(
        "overrides",
        [
            {"intensity": 0},
            {"intensity": 6},
            {"duration_minutes": -5},
            {"duration_minutes": 24 * 60 + 1},
            {"what_helped": "x" * 201},
            {"occurred_at": "not a time"},
        ],
    )
    def test_rejects_invalid_values(self, auth_client, overrides):
        response = auth_client.post(EPISODES, self.payload(**overrides), format="json")
        assert response.status_code == 400
        assert set(response.json()) == set(overrides)

    def test_rejects_a_time_in_the_future(self, auth_client):
        later = (timezone.now() + timedelta(hours=2)).isoformat()
        response = auth_client.post(EPISODES, self.payload(occurred_at=later), format="json")
        assert response.status_code == 400
        assert "occurred_at" in response.json()

    def test_requires_time_and_intensity(self, auth_client):
        response = auth_client.post(EPISODES, {}, format="json")
        assert response.status_code == 400
        assert set(response.json()) == {"occurred_at", "intensity"}

    def test_helped_exercise_must_be_reviewed_content(self, auth_client):
        unreviewed = ExerciseFactory(review_status="needs_review")
        response = auth_client.post(
            EPISODES, self.payload(helped_exercise=str(unreviewed.pk)), format="json"
        )
        assert response.status_code == 400

    def test_deleting_a_trigger_keeps_the_episode(self, auth_client, user):
        trigger = TriggerFactory(user=user)
        episode = EpisodeFactory(user=user, trigger=trigger)
        assert auth_client.delete(f"{TRIGGERS}/{trigger.pk}").status_code == 204
        episode.refresh_from_db()
        assert episode.trigger is None

    def test_list_is_newest_first_and_paginated(self, auth_client, user):
        now = timezone.now()
        for hours in range(1, 24):
            EpisodeFactory(user=user, occurred_at=now - timedelta(hours=hours))
        body = auth_client.get(EPISODES).json()
        assert body["count"] == 23 and len(body["results"]) == 20
        times = [row["occurred_at"] for row in body["results"]]
        assert times == sorted(times, reverse=True)

    def test_response_fields_and_no_diagnostic_fields(self, auth_client, user):
        EpisodeFactory(user=user)
        row = auth_client.get(EPISODES).json()["results"][0]
        assert set(row) == {
            "id",
            "occurred_at",
            "intensity",
            "duration_minutes",
            "trigger",
            "helped_exercise",
            "what_helped",
            "created_at",
        }
        field_names = {f.name for f in Episode._meta.get_fields()} | {
            f.name for f in Trigger._meta.get_fields()
        }
        for banned in ("diagnosis", "type", "category", "severity", "description", "risk"):
            assert banned not in field_names


class TestConstraints:
    def test_database_rejects_out_of_range_intensity(self, user):
        with pytest.raises(IntegrityError), transaction.atomic():
            EpisodeFactory(user=user, intensity=9)

    def test_database_rejects_overlong_duration(self, user):
        with pytest.raises(IntegrityError), transaction.atomic():
            EpisodeFactory(user=user, duration_minutes=5000)


class TestNothingSensitiveIsLogged:
    def test_trigger_and_episode_text_never_reach_the_logs(self, auth_client, caplog):
        import json
        import logging

        caplog.set_level(logging.DEBUG)
        trigger_id = auth_client.post(TRIGGERS, {"label": CANARY}, format="json").json()["id"]
        auth_client.post(TRIGGERS, {"label": CANARY}, format="json")  # duplicate -> 400
        auth_client.post(
            EPISODES,
            {
                "occurred_at": timezone.now().isoformat(),
                "intensity": 3,
                "trigger": trigger_id,
                "what_helped": CANARY,
            },
            format="json",
        )
        auth_client.get("/api/v1/export")

        logged = "\n".join(
            f"{r.getMessage()} {json.dumps(r.__dict__, default=str)}" for r in caplog.records
        )
        assert CANARY not in logged
        assert CANARY not in str(Trigger.objects.get(pk=trigger_id))
        assert CANARY not in repr(Episode.objects.get())
