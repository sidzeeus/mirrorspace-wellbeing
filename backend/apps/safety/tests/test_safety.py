from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from apps.safety.models import Resource, SafetyPlan
from tests.factories import ResourceFactory
from tests.harness import SingletonResourceContract, client_for

pytestmark = pytest.mark.django_db

PLAN = "/api/v1/safety-plan"
RESOURCES = "/api/v1/resources"
CANARY = "CANARY-safety-plan-private-words"


class TestSafetyPlanIsolation(SingletonResourceContract):
    url = PLAN
    payload = {
        "warning_signs": [f"{CANARY}-sign"],
        "coping_steps": [f"{CANARY}-step"],
        "people": [f"{CANARY}-person"],
    }


class TestSafetyPlan:
    def test_starts_empty_and_stores_nothing(self, auth_client, user):
        body = auth_client.get(PLAN).json()
        assert body == {
            "warning_signs": [],
            "coping_steps": [],
            "people": [],
            "resource_ids": [],
            "updated_at": None,
        }
        assert not SafetyPlan.objects.filter(user=user).exists()

    def test_put_creates_then_replaces(self, auth_client, user):
        first = auth_client.put(PLAN, {"warning_signs": ["Skipping meals"]}, format="json")
        second = auth_client.put(
            PLAN,
            {"warning_signs": ["Not sleeping"], "coping_steps": ["Walk outside"], "people": []},
            format="json",
        )
        assert first.status_code == second.status_code == 200
        assert SafetyPlan.objects.filter(user=user).count() == 1
        assert auth_client.get(PLAN).json()["warning_signs"] == ["Not sleeping"]
        assert auth_client.get(PLAN).json()["coping_steps"] == ["Walk outside"]

    def test_blank_lines_are_dropped_and_text_is_trimmed(self, auth_client):
        response = auth_client.put(
            PLAN, {"coping_steps": ["  Breathe  ", "", "   "]}, format="json"
        )
        assert response.json()["coping_steps"] == ["Breathe"]

    def test_limits_on_size(self, auth_client):
        too_many = auth_client.put(PLAN, {"people": ["x"] * 13}, format="json")
        too_long = auth_client.put(PLAN, {"people": ["x" * 201]}, format="json")
        not_a_list = auth_client.put(PLAN, {"people": "just text"}, format="json")
        assert too_many.status_code == too_long.status_code == not_a_list.status_code == 400

    def test_everything_written_is_encrypted_in_the_database(self, auth_client, user):
        auth_client.put(
            PLAN,
            {
                "warning_signs": [f"{CANARY}-1"],
                "coping_steps": [f"{CANARY}-2"],
                "people": [f"{CANARY}-3"],
            },
            format="json",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT warning_signs, coping_steps, people "
                "FROM safety_safetyplan WHERE user_id = %s",
                [user.pk],
            )
            stored = cursor.fetchone()
        assert all(value.startswith("gAAAA") for value in stored)
        assert CANARY not in "".join(stored)

    def test_can_pick_verified_resources_only(self, auth_client):
        verified = ResourceFactory()
        unverified = ResourceFactory(status="needs_review")

        ok = auth_client.put(PLAN, {"resource_ids": [str(verified.pk)]}, format="json")
        bad = auth_client.put(PLAN, {"resource_ids": [str(unverified.pk)]}, format="json")

        assert ok.json()["resource_ids"] == [str(verified.pk)]
        assert bad.status_code == 400

    def test_delete_clears_the_plan(self, auth_client, user):
        auth_client.put(PLAN, {"warning_signs": ["x"]}, format="json")
        assert auth_client.delete(PLAN).status_code == 204
        assert not SafetyPlan.objects.filter(user=user).exists()
        assert auth_client.get(PLAN).json()["warning_signs"] == []

    def test_plan_text_never_reaches_the_logs(self, auth_client, caplog):
        import json
        import logging

        caplog.set_level(logging.DEBUG)
        auth_client.put(PLAN, {"warning_signs": [CANARY], "people": ["x" * 500]}, format="json")
        auth_client.put(PLAN, {"warning_signs": [CANARY]}, format="json")
        auth_client.get(PLAN)
        logged = "\n".join(
            f"{r.getMessage()} {json.dumps(r.__dict__, default=str)}" for r in caplog.records
        )
        assert CANARY not in logged
        assert CANARY not in str(SafetyPlan.objects.get())

    def test_plan_is_not_in_the_admin(self):
        from django.contrib import admin

        assert SafetyPlan not in admin.site._registry


class TestResources:
    def test_public_so_helplines_show_before_sign_up(self, api_client):
        ResourceFactory()
        response = api_client.get(RESOURCES)
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_only_verified_entries_are_served(self, api_client):
        ResourceFactory(slug="verified")
        ResourceFactory(slug="waiting", status="needs_review", verified_on=None)
        ResourceFactory(slug="draft", status="draft")
        ResourceFactory(slug="retired", status="retired")
        assert [r["slug"] for r in api_client.get(RESOURCES).json()["results"]] == ["verified"]

    def test_fields_include_region_language_type_source_and_date(self, api_client):
        ResourceFactory()
        row = api_client.get(RESOURCES).json()["results"][0]
        assert set(row) == {
            "id",
            "slug",
            "name",
            "description",
            "type",
            "region",
            "languages",
            "phone",
            "url",
            "hours",
            "source",
            "verified_on",
            "stale",
            "reviewed",
        }
        assert row["stale"] is False and row["reviewed"] is True

    def test_old_verification_is_flagged_stale_but_still_shown(self, api_client, settings):
        old = timezone.localdate() - timedelta(days=settings.RESOURCE_MAX_AGE_DAYS + 1)
        ResourceFactory(slug="old", verified_on=old)
        row = api_client.get(RESOURCES).json()["results"][0]
        assert row["stale"] is True
        assert row["verified_on"] == old.isoformat()

    def test_filters(self, api_client):
        ResourceFactory(slug="in-hi", region="IN", languages=["hi"], type="helpline")
        ResourceFactory(slug="in-ka", region="IN-KA", languages=["kn"], type="campus")
        ResourceFactory(slug="gb", region="GB", languages=["en"], type="emergency")

        def found(query):
            return {r["slug"] for r in api_client.get(f"{RESOURCES}?{query}").json()["results"]}

        assert found("region=IN") == {"in-hi", "in-ka"}
        assert found("region=IN-KA") == {"in-ka"}
        assert found("language=hi") == {"in-hi"}
        assert found("type=emergency") == {"gb"}

    def test_read_only(self, auth_client):
        resource = ResourceFactory()
        assert auth_client.post(RESOURCES, {"name": "x"}, format="json").status_code == 405
        assert auth_client.delete(f"{RESOURCES}/{resource.pk}").status_code == 405

    def test_development_switch_shows_placeholders_as_unverified(self, api_client, settings):
        ResourceFactory(slug="waiting", status="needs_review", verified_on=None)
        settings.SHOW_UNREVIEWED_CONTENT = True
        row = api_client.get(RESOURCES).json()["results"][0]
        assert (row["reviewed"], row["stale"], row["verified_on"]) == (False, True, None)


class TestSeedResources:
    def run(self):
        out = io.StringIO()
        call_command("seed_resources", stdout=out)
        return out.getvalue()

    def test_loads_tele_manas_as_an_unverified_placeholder(self, api_client):
        output = self.run()
        tele_manas = Resource.objects.get(slug="in-tele-manas")

        assert "NEEDS_HUMAN_REVIEW" in output
        assert (tele_manas.phone, tele_manas.region) == ("14416", "IN")
        assert tele_manas.status == "needs_review"
        assert tele_manas.verified_on is None
        assert set(Resource.objects.values_list("status", flat=True)) == {"needs_review"}
        # Hidden from students until a person verifies it.
        assert api_client.get(RESOURCES).json()["count"] == 0

    def test_is_idempotent_and_never_overwrites_verified_entries(self):
        self.run()
        count = Resource.objects.count()
        entry = Resource.objects.get(slug="in-tele-manas")
        entry.status, entry.phone, entry.verified_on = "approved", "99999", timezone.localdate()
        entry.owner = "A Person"
        entry.save()

        self.run()

        entry.refresh_from_db()
        assert Resource.objects.count() == count
        assert (entry.status, entry.phone, entry.owner) == ("approved", "99999", "A Person")
        assert entry.verified_on is not None


class TestFlagStaleResources:
    def run(self, *args):
        out = io.StringIO()
        call_command("flag_stale_resources", *args, stdout=out)
        return out.getvalue()

    def test_flags_old_and_never_verified_entries(self):
        fresh = ResourceFactory(slug="fresh")
        old = ResourceFactory(slug="old", verified_on=timezone.localdate() - timedelta(days=200))
        never = ResourceFactory(slug="never", verified_on=None, status="needs_review")
        retired = ResourceFactory(slug="retired", verified_on=None, status="retired")

        output = self.run()

        for resource in (fresh, old, never, retired):
            resource.refresh_from_db()
        assert old.flagged_stale_at is not None and never.flagged_stale_at is not None
        assert fresh.flagged_stale_at is None and retired.flagged_stale_at is None
        assert "old" in output and "never" in output and "Test Owner" in output
        assert "fresh" not in output.replace("re-verification", "")

    def test_age_is_configurable(self):
        resource = ResourceFactory(verified_on=timezone.localdate() - timedelta(days=10))
        self.run("--max-age-days", "30")
        resource.refresh_from_db()
        assert resource.flagged_stale_at is None

        self.run("--max-age-days", "5")
        resource.refresh_from_db()
        assert resource.flagged_stale_at is not None

    def test_flag_clears_only_when_a_person_reverifies(self):
        resource = ResourceFactory(verified_on=timezone.localdate() - timedelta(days=200))
        self.run()
        self.run()
        resource.refresh_from_db()
        assert resource.flagged_stale_at is not None

        resource.verified_on = timezone.localdate()
        resource.save()
        self.run()
        resource.refresh_from_db()
        assert resource.flagged_stale_at is None

    def test_can_fail_a_pipeline(self):
        ResourceFactory(verified_on=None)
        with pytest.raises(SystemExit) as exit_info:
            self.run("--fail-on-stale")
        assert exit_info.value.code == 1

    def test_reports_cleanly_when_nothing_is_stale(self):
        ResourceFactory()
        assert "All resources were verified" in self.run("--fail-on-stale")

    def test_never_changes_a_phone_number(self):
        resource = ResourceFactory(phone="14416", verified_on=None)
        self.run()
        resource.refresh_from_db()
        assert resource.phone == "14416"


def test_other_users_plan_is_unreachable_even_with_its_id(user, other_user):
    """There is no route that takes a plan id at all."""
    plan = SafetyPlan.objects.create(user=other_user, warning_signs=[CANARY])
    client = client_for(user)
    for url in (f"{PLAN}/{plan.pk}", f"{PLAN}?id={plan.pk}", f"{PLAN}?user={other_user.pk}"):
        response = client.get(url)
        assert CANARY not in response.content.decode()
