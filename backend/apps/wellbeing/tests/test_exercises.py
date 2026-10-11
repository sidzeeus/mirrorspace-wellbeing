from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from apps.wellbeing.models import (
    Exercise,
    ExerciseEvent,
    ExerciseTranslation,
    ReviewStatus,
)
from tests.factories import ExerciseEventFactory, ExerciseFactory
from tests.harness import OwnedResourceContract, client_for

pytestmark = pytest.mark.django_db

EXERCISES = "/api/v1/exercises"
EVENTS = "/api/v1/exercise-events"


def slugs(response):
    return [row["slug"] for row in response.json()["results"]]


class TestExerciseEventIsolation(OwnedResourceContract):
    list_url = EVENTS
    detail_methods = ("get", "delete")

    def make(self, user):
        return ExerciseEventFactory(user=user)


class TestExerciseLibrary:
    def test_requires_sign_in(self, api_client):
        ExerciseFactory()
        assert api_client.get(EXERCISES).status_code == 401

    def test_only_approved_content_is_shown(self, auth_client):
        ExerciseFactory(slug="approved")
        ExerciseFactory(slug="draft", review_status=ReviewStatus.DRAFT)
        ExerciseFactory(slug="waiting", review_status=ReviewStatus.NEEDS_REVIEW)
        ExerciseFactory(slug="retired", review_status=ReviewStatus.RETIRED)
        ExerciseFactory(slug="text-unreviewed", translations__review_status="needs_review")

        assert slugs(auth_client.get(EXERCISES)) == ["approved"]

    def test_unapproved_exercise_cannot_be_opened_directly(self, auth_client):
        hidden = ExerciseFactory(review_status=ReviewStatus.NEEDS_REVIEW)
        assert auth_client.get(f"{EXERCISES}/{hidden.pk}").status_code == 404

    def test_development_switch_shows_placeholders_labelled_unreviewed(self, auth_client, settings):
        ExerciseFactory(slug="approved")
        ExerciseFactory(
            slug="waiting",
            review_status=ReviewStatus.NEEDS_REVIEW,
            translations__review_status="needs_review",
        )
        ExerciseFactory(slug="draft", review_status=ReviewStatus.DRAFT)
        settings.SHOW_UNREVIEWED_CONTENT = True

        rows = {row["slug"]: row for row in auth_client.get(EXERCISES).json()["results"]}

        assert set(rows) == {"approved", "waiting"}
        assert rows["approved"]["reviewed"] is True
        assert rows["waiting"]["reviewed"] is False

    def test_response_fields(self, auth_client):
        ExerciseFactory()
        row = auth_client.get(EXERCISES).json()["results"][0]
        assert set(row) == {
            "id",
            "slug",
            "category",
            "duration_minutes",
            "pattern",
            "title",
            "summary",
            "steps",
            "language",
            "hidden",
            "reviewed",
        }
        assert row["steps"] == ["First step.", "Second step."]

    def test_filter_by_category(self, auth_client):
        ExerciseFactory(slug="a", category="breathing")
        ExerciseFactory(slug="b", category="movement")
        assert slugs(auth_client.get(f"{EXERCISES}?category=breathing")) == ["a"]
        assert len(slugs(auth_client.get(f"{EXERCISES}?category=nonsense"))) == 2


class TestLanguage:
    def make_bilingual(self, hindi_status="approved"):
        exercise = ExerciseFactory(slug="bilingual")
        ExerciseTranslation.objects.create(
            exercise=exercise,
            language="hi",
            title="Hindi title",
            summary="Hindi summary",
            steps=["Hindi step"],
            review_status=hindi_status,
        )
        return exercise

    def test_uses_the_persons_preferred_language(self, auth_client, user):
        self.make_bilingual()
        user.preferred_language = "hi"
        user.save()
        row = auth_client.get(EXERCISES).json()["results"][0]
        assert (row["language"], row["title"]) == ("hi", "Hindi title")

    def test_query_parameter_overrides_preference(self, auth_client):
        self.make_bilingual()
        row = auth_client.get(f"{EXERCISES}?lang=hi").json()["results"][0]
        assert row["language"] == "hi"

    def test_falls_back_to_english_when_the_translation_is_not_approved(self, auth_client):
        self.make_bilingual(hindi_status="needs_review")
        row = auth_client.get(f"{EXERCISES}?lang=hi").json()["results"][0]
        assert (row["language"], row["title"]) == ("en", "Title of bilingual")

    def test_exercise_with_no_approved_text_is_left_out(self, auth_client):
        exercise = ExerciseFactory(slug="hindi-only", translations=False)
        ExerciseTranslation.objects.create(
            exercise=exercise,
            language="hi",
            title="t",
            summary="s",
            steps=[],
            review_status="approved",
        )
        assert slugs(auth_client.get(f"{EXERCISES}?lang=en")) == []
        assert slugs(auth_client.get(f"{EXERCISES}?lang=hi")) == ["hindi-only"]

    def test_exercise_is_not_duplicated_when_two_languages_match(self, auth_client):
        self.make_bilingual()
        assert slugs(auth_client.get(f"{EXERCISES}?lang=hi")) == ["bilingual"]


class TestFeedback:
    def post(self, client, exercise, kind):
        return client.post(EVENTS, {"exercise": str(exercise.pk), "kind": kind}, format="json")

    def test_not_helpful_is_recorded_for_the_signed_in_person(self, auth_client, user):
        exercise = ExerciseFactory()
        response = self.post(auth_client, exercise, "not_helpful")
        assert response.status_code == 201
        event = ExerciseEvent.objects.get()
        assert (event.user_id, event.exercise_id, event.kind) == (
            user.pk,
            exercise.pk,
            "not_helpful",
        )
        assert "user" not in response.json()

    def test_hide_this_removes_it_from_my_list_only(self, auth_client, other_user):
        ExerciseFactory(slug="keep")
        hide = ExerciseFactory(slug="hide")
        self.post(auth_client, hide, "hidden")

        assert slugs(auth_client.get(EXERCISES)) == ["keep"]
        assert set(slugs(client_for(other_user).get(EXERCISES))) == {"keep", "hide"}

    def test_hidden_exercises_can_be_listed_and_shown_again(self, auth_client):
        exercise = ExerciseFactory(slug="hide")
        self.post(auth_client, exercise, "hidden")

        with_hidden = auth_client.get(f"{EXERCISES}?include_hidden=true").json()["results"]
        assert [(r["slug"], r["hidden"]) for r in with_hidden] == [("hide", True)]
        assert auth_client.get(f"{EXERCISES}/{exercise.pk}").json()["hidden"] is True

        self.post(auth_client, exercise, "unhidden")
        row = auth_client.get(EXERCISES).json()["results"][0]
        assert (row["slug"], row["hidden"]) == ("hide", False)

    def test_feedback_can_be_removed(self, auth_client, user):
        event = ExerciseEventFactory(user=user)
        assert auth_client.delete(f"{EVENTS}/{event.pk}").status_code == 204
        assert not ExerciseEvent.objects.filter(pk=event.pk).exists()

    def test_feedback_cannot_be_edited(self, auth_client, user):
        event = ExerciseEventFactory(user=user)
        assert (
            auth_client.patch(
                f"{EVENTS}/{event.pk}", {"kind": "helpful"}, format="json"
            ).status_code
            == 405
        )

    def test_rejects_unknown_kind_and_unreviewed_exercise(self, auth_client):
        approved = ExerciseFactory()
        unreviewed = ExerciseFactory(review_status=ReviewStatus.NEEDS_REVIEW)
        assert self.post(auth_client, approved, "loved_it").status_code == 400
        assert self.post(auth_client, unreviewed, "completed").status_code == 400

    def test_owner_comes_from_the_session(self, auth_client, user, other_user):
        exercise = ExerciseFactory()
        auth_client.post(
            EVENTS,
            {"exercise": str(exercise.pk), "kind": "completed", "user": str(other_user.pk)},
            format="json",
        )
        assert ExerciseEvent.objects.get().user_id == user.pk


class TestSeedCommand:
    def run(self) -> str:
        out = io.StringIO()
        call_command("seed_exercises", stdout=out)
        return out.getvalue()

    def test_loads_placeholders_flagged_for_review(self):
        output = self.run()
        assert "NEEDS_HUMAN_REVIEW" in output
        assert Exercise.objects.count() >= 6
        assert set(Exercise.objects.values_list("review_status", flat=True)) == {"needs_review"}
        assert set(ExerciseTranslation.objects.values_list("review_status", flat=True)) == {
            "needs_review"
        }
        categories = set(Exercise.objects.values_list("category", flat=True))
        assert categories == {
            "grounding",
            "breathing",
            "journaling",
            "planning",
            "movement",
            "wind_down",
        }

    def test_seeded_content_is_invisible_to_students_by_default(self, auth_client):
        self.run()
        assert auth_client.get(EXERCISES).json()["count"] == 0

    def test_running_twice_creates_nothing_new(self):
        self.run()
        before = (Exercise.objects.count(), ExerciseTranslation.objects.count())
        self.run()
        assert (Exercise.objects.count(), ExerciseTranslation.objects.count()) == before

    def test_never_overwrites_or_downgrades_approved_content(self):
        self.run()
        exercise = Exercise.objects.get(slug="five-senses")
        exercise.review_status = ReviewStatus.APPROVED
        exercise.duration_minutes = 9
        exercise.save()
        translation = exercise.translations.get(language="en")
        translation.review_status = ReviewStatus.APPROVED
        translation.title = "Clinician's wording"
        translation.save()

        self.run()

        exercise.refresh_from_db()
        translation.refresh_from_db()
        assert (exercise.review_status, exercise.duration_minutes) == ("approved", 9)
        assert (translation.review_status, translation.title) == ("approved", "Clinician's wording")

    def test_breathing_placeholder_has_a_pace(self):
        self.run()
        assert Exercise.objects.get(category="breathing").pattern == {"inhale": 4, "exhale": 6}
