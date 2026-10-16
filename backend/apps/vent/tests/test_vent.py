from __future__ import annotations

import json
import logging

import pytest
from django.db import connection

from apps.audit.models import AuditEvent
from apps.notifications.models import Notification
from apps.vent.models import VentEntry
from apps.vent.reactions import REACTIONS, react
from tests.factories import UserFactory
from tests.harness import OwnedResourceContract, client_for

pytestmark = pytest.mark.django_db

ENTRIES = "/api/v1/vent-entries"
REFLECT = "/api/v1/vent/reflect"
CANARY = "CANARY-private-vent-words"


def raw_body(pk) -> str:
    with connection.cursor() as cursor:
        cursor.execute('SELECT "body" FROM "vent_vententry" WHERE id = %s', [pk])
        return cursor.fetchone()[0]


class TestVentEntryIsolation(OwnedResourceContract):
    list_url = ENTRIES
    detail_methods = ("get", "delete")

    def make(self, user):
        return VentEntry.objects.create(user=user, body="mine alone")


class TestReactions:
    """The figure reacts to words. It is a mirror, not an assessment."""

    @pytest.mark.parametrize(
        ("text", "kind"),
        [
            ("I feel so tired and empty, I just keep crying", "heavy"),
            ("I am so angry and furious, this is unfair and I hate it", "storm"),
            ("I'm so anxious and nervous, overthinking everything about tomorrow", "racing"),
            ("Nobody talks to me, I feel so lonely and left out", "alone"),
            ("Today felt lighter, I'm grateful and a bit hopeful", "lighter"),
            ("Bought groceries, wrote some notes about the lecture", "listening"),
            ("bahut akela feel ho raha hai", "alone"),
        ],
    )
    def test_reacts_to_the_words_used(self, text, kind):
        assert react(text).kind == kind

    def test_every_reaction_is_known(self):
        kinds = {react(t).kind for t in ["sad", "angry", "anxious", "lonely", "hopeful", "ok"]}
        assert kinds <= set(REACTIONS)

    @pytest.mark.parametrize(
        "text",
        [
            "I am grateful for my friends but I want to kill myself",
            "main mar jana chahta hoon",
            "I'm going to end my life tonight",
        ],
    )
    def test_crisis_wording_always_wins_and_gets_the_steady_reaction(self, text):
        reaction = react(text)
        assert reaction.level == "crisis"
        assert reaction.kind == "steady"

    def test_panic_gets_the_breathing_reaction_with_support(self):
        reaction = react("I'm panicking and I can't breathe")
        assert reaction.level == "distress"
        assert reaction.kind == "racing"

    def test_negation_does_not_count_as_hopeful(self):
        assert react("I am not hopeful and not okay at all, so sad").kind == "heavy"


class TestReflect:
    def test_returns_a_reaction_and_stores_nothing(self, auth_client):
        response = auth_client.post(REFLECT, {"text": f"so lonely {CANARY}"}, format="json")
        assert response.status_code == 200
        assert response.json() == {"reaction": "alone", "level": None}
        assert VentEntry.objects.count() == 0

    def test_crisis_reply_points_to_support_and_alerts_nobody(self, auth_client):
        response = auth_client.post(REFLECT, {"text": "I want to kill myself"}, format="json")
        assert response.json() == {"reaction": "steady", "level": "crisis"}
        assert Notification.objects.count() == 0
        assert VentEntry.objects.count() == 0

    def test_needs_sign_in_and_text(self, api_client, auth_client):
        assert api_client.post(REFLECT, {"text": "hello"}, format="json").status_code == 401
        assert auth_client.post(REFLECT, {"text": "   "}, format="json").status_code == 400
        too_long = {"text": "x" * 5001}
        assert auth_client.post(REFLECT, too_long, format="json").status_code == 400


class TestKeptEntries:
    def test_keeping_is_explicit_and_encrypted(self, auth_client):
        created = auth_client.post(ENTRIES, {"body": f"my heart out {CANARY}"}, format="json")
        assert created.status_code == 201
        entry_id = created.json()["id"]
        stored = raw_body(entry_id)
        assert CANARY not in stored
        assert stored.startswith("gAAAA")
        assert auth_client.get(f"{ENTRIES}/{entry_id}").json()["body"].endswith(CANARY)

    def test_entries_cannot_be_edited_only_deleted(self, auth_client):
        entry_id = auth_client.post(ENTRIES, {"body": "first"}, format="json").json()["id"]
        assert (
            auth_client.patch(f"{ENTRIES}/{entry_id}", {"body": "x"}, format="json").status_code
            == 405
        )
        assert auth_client.delete(f"{ENTRIES}/{entry_id}").status_code == 204
        assert VentEntry.objects.count() == 0

    def test_newest_first_and_validated(self, auth_client):
        auth_client.post(ENTRIES, {"body": "older"}, format="json")
        auth_client.post(ENTRIES, {"body": "newer"}, format="json")
        bodies = [e["body"] for e in auth_client.get(ENTRIES).json()["results"]]
        assert bodies == ["newer", "older"]
        assert auth_client.post(ENTRIES, {"body": "  "}, format="json").status_code == 400
        assert auth_client.post(ENTRIES, {"body": "x" * 5001}, format="json").status_code == 400

    def test_no_reaction_or_label_is_stored(self):
        fields = {field.name for field in VentEntry._meta.get_fields()}
        assert fields == {"id", "user", "body", "created_at"}

    def test_exported_and_erased_with_the_account(self):
        from apps.accounts.export import build_export
        from apps.accounts.services import _erase

        user = UserFactory()
        VentEntry.objects.create(user=user, body="exported words")
        assert [e["body"] for e in build_export(user)["vent_entries"]] == ["exported words"]
        _erase(user)
        assert VentEntry.objects.count() == 0


def test_nothing_written_reaches_logs_or_the_audit_trail(auth_client, caplog):
    caplog.set_level(logging.DEBUG)
    auth_client.post(REFLECT, {"text": f"so angry {CANARY}"}, format="json")
    auth_client.post(REFLECT, {"text": f"I want to die {CANARY}"}, format="json")
    entry = auth_client.post(ENTRIES, {"body": CANARY}, format="json").json()
    auth_client.get(f"{ENTRIES}/{entry['id']}")

    logged = "\n".join(
        f"{r.getMessage()} {json.dumps(r.__dict__, default=str)}" for r in caplog.records
    )
    assert CANARY not in logged
    assert "angry" not in logged
    assert CANARY not in json.dumps(list(AuditEvent.objects.values()), default=str)


def test_reflect_is_rate_limited(settings, auth_client):
    from django.core.cache import cache

    cache.clear()
    for _ in range(30):
        assert auth_client.post(REFLECT, {"text": "hello"}, format="json").status_code == 200
    assert auth_client.post(REFLECT, {"text": "hello"}, format="json").status_code == 429


def test_another_users_entries_never_appear(auth_client):
    VentEntry.objects.create(user=UserFactory(), body="someone else")
    assert client_for(UserFactory()).get(ENTRIES).json()["count"] == 0
    assert auth_client.get(ENTRIES).json()["count"] == 0
