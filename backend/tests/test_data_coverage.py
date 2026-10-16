"""Export and deletion must cover every piece of data a student owns.

These tests discover models by introspection, so adding a new user-owned model in a
later phase fails here until it is exportable and is erased with the account.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet, InvalidToken
from django.apps import apps
from django.db import models
from django.utils import timezone

from apps.accounts import export, services
from apps.accounts.models import User
from apps.audit.models import AuditEvent
from config import fields
from tests.factories import (
    DEFAULT_PASSWORD,
    CheckInFactory,
    EpisodeFactory,
    ExerciseEventFactory,
    ExerciseFactory,
    TriggerFactory,
    TrustedContactFactory,
    UserFactory,
)

EXPORT = "/api/v1/export"
CANARY = "CANARY-export-private-words"


def user_owned_models() -> list[type[models.Model]]:
    """Project models with a direct foreign key or one-to-one link to the user."""
    owned = []
    for model in apps.get_models():
        if not model.__module__.startswith("apps."):
            continue
        for field in model._meta.get_fields():
            if (
                isinstance(field, models.ForeignKey | models.OneToOneField)
                and field.related_model is User
            ):
                owned.append(model)
                break
    return owned


# Models that deliberately outlive the account, and why. Anything else linked to a
# user must be deleted with it. Adding to this list is a privacy decision: record it in
# docs/decisions.md and docs/privacy.md.
SURVIVES_DELETION = {AuditEvent: "pseudonymized, then purged after the retention period (D5)"}


def populate(user):
    exercise = ExerciseFactory()
    trigger = TriggerFactory(user=user, label=f"{CANARY}-label")
    trigger.preferred_exercises.add(exercise)
    return {
        "check_in": CheckInFactory(user=user, mood=4, sleep_hours="6.5"),
        "trigger": trigger,
        "episode": EpisodeFactory(
            user=user, trigger=trigger, helped_exercise=exercise, what_helped=f"{CANARY}-helped"
        ),
        "event": ExerciseEventFactory(user=user, exercise=exercise, kind="not_helpful"),
        "exercise": exercise,
        **populate_sharing(user),
    }


def populate_sharing(user):
    from apps.audit.services import record
    from apps.notifications.models import Notification
    from apps.safety.models import SafetyPlan
    from apps.sharing.models import ConsentRecord

    contact = TrustedContactFactory(user=user, name=f"{CANARY}-contact")
    now = timezone.now()
    consent = ConsentRecord.objects.create(
        user=user,
        contact=contact,
        purpose="weekly_summary",
        scope=["display_name"],
        notice_version="v-test",
        granted_at=now,
        last_confirmed_at=now,
    )
    return {
        "plan": SafetyPlan.objects.create(user=user, warning_signs=[f"{CANARY}-sign"]),
        "contact": contact,
        "consent": consent,
        "notification": Notification.objects.create(
            user=user,
            purpose="weekly_summary",
            contact=contact,
            consent=consent,
            idempotency_key=f"test:{contact.pk}",
            scheduled_at=now,
        ),
        "audit": record("consent.granted", user=user, obj=consent, purpose="weekly_summary"),
        **populate_chat(user),
    }


def populate_chat(user):
    from apps.chat.models import ChatFeedback, ChatMessage, ChatSession, ChatUsage

    session = ChatSession.objects.create(user=user, save_transcript=True, expires_at=timezone.now())
    ChatMessage.objects.create(session=session, role="user", content=f"{CANARY}-chat")
    ChatFeedback.objects.create(user=user, session=session, kind="answer", helpful=True)
    ChatUsage.objects.create(user=user, day=timezone.localdate(), replies=2)
    return {"chat_session": session, **populate_vent(user)}


def populate_vent(user):
    from apps.vent.models import VentEntry

    return {"vent_entry": VentEntry.objects.create(user=user, body=f"{CANARY}-vent")}


class TestCoverageByIntrospection:
    def test_there_are_user_owned_models_to_check(self):
        names = {m.__name__ for m in user_owned_models()}
        assert {"Profile", "CheckIn", "Trigger", "Episode", "ExerciseEvent"} <= names

    def test_every_user_owned_model_is_in_the_export(self):
        missing = [m.__name__ for m in user_owned_models() if m not in export.covered_models()]
        assert missing == [], f"not included in the data export: {missing}"

    def test_every_user_owned_model_is_erased_with_the_account(self):
        not_cascading = []
        for model in user_owned_models():
            for field in model._meta.get_fields():
                if (
                    isinstance(field, models.ForeignKey | models.OneToOneField)
                    and field.related_model is User
                    and field.remote_field.on_delete is not models.CASCADE
                    and model not in SURVIVES_DELETION
                ):
                    not_cascading.append(f"{model.__name__}.{field.name}")
        assert not_cascading == [], f"would survive account deletion: {not_cascading}"


@pytest.mark.django_db
class TestExport:
    def test_requires_sign_in(self, api_client):
        assert api_client.get(EXPORT).status_code == 401

    def test_contains_everything_the_person_owns(self, auth_client, user):
        made = populate(user)
        response = auth_client.get(EXPORT)
        body = response.json()

        assert response.status_code == 200
        assert set(body) == {
            "format_version",
            "exported_at",
            "account",
            "check_ins",
            "triggers",
            "episodes",
            "exercise_events",
            "safety_plan",
            "trusted_contacts",
            "consents",
            "notifications",
            "audit_events",
            "vent_entries",
            "chat",
        }
        assert body["chat"]["sessions"][0]["messages"][0]["content"] == f"{CANARY}-chat"
        assert body["chat"]["feedback"][0]["helpful"] is True
        assert body["chat"]["usage"][0]["replies"] == 2
        assert body["safety_plan"]["warning_signs"] == [f"{CANARY}-sign"]
        assert body["trusted_contacts"][0]["name"] == f"{CANARY}-contact"
        assert body["consents"][0]["notice_version"] == "v-test"
        assert body["notifications"][0]["purpose"] == "weekly_summary"
        assert "consent.granted" in [e["action"] for e in body["audit_events"]]
        assert body["account"]["email"] == user.email
        assert body["check_ins"][0]["mood"] == 4 and body["check_ins"][0]["sleep_hours"] == 6.5
        assert body["triggers"][0]["label"] == f"{CANARY}-label"
        assert body["triggers"][0]["preferred_exercises"] == [made["exercise"].slug]
        assert body["episodes"][0]["what_helped"] == f"{CANARY}-helped"
        assert body["episodes"][0]["trigger_id"] == str(made["trigger"].pk)
        assert body["exercise_events"][0]["kind"] == "not_helpful"

    def test_is_a_download_that_is_not_cached(self, auth_client):
        response = auth_client.get(EXPORT)
        assert "attachment" in response.headers["Content-Disposition"]
        assert response.headers["Cache-Control"] == "no-store"

    def test_never_includes_secrets(self, auth_client, user):
        dumped = json.dumps(auth_client.get(EXPORT).json())
        assert "password" not in dumped
        assert user.password not in dumped

    def test_contains_nothing_from_another_person(self, auth_client, user, other_user):
        populate(user)
        theirs = populate(other_user)
        dumped = json.dumps(auth_client.get(EXPORT).json())

        assert other_user.email not in dumped
        assert str(other_user.pk) not in dumped
        for key in (
            "check_in",
            "trigger",
            "episode",
            "event",
            "contact",
            "consent",
            "notification",
            "chat_session",
        ):
            assert str(theirs[key].pk) not in dumped

    def test_is_rate_limited(self, auth_client):
        statuses = [auth_client.get(EXPORT).status_code for _ in range(11)]
        assert statuses[:10] == [200] * 10 and statuses[10] == 429

    def test_empty_account_exports_empty_lists(self, auth_client):
        body = auth_client.get(EXPORT).json()
        assert body["check_ins"] == body["triggers"] == body["episodes"] == []
        assert body["trusted_contacts"] == body["consents"] == body["notifications"] == []
        assert body["safety_plan"] is None
        assert body["chat"] == {"sessions": [], "feedback": [], "usage": []}


@pytest.mark.django_db
class TestDeletion:
    def test_deleting_the_account_removes_every_owned_row(self, auth_client, user, other_user):
        populate(user)
        populate(other_user)

        response = auth_client.delete(
            "/api/v1/account", {"password": DEFAULT_PASSWORD}, format="json"
        )

        assert response.status_code == 202
        for model in user_owned_models():
            if model in SURVIVES_DELETION:
                continue
            field = next(
                f.name
                for f in model._meta.get_fields()
                if isinstance(f, models.ForeignKey | models.OneToOneField)
                and f.related_model is User
            )
            assert not model._default_manager.filter(**{f"{field}_id": user.pk}).exists(), (
                f"{model.__name__} rows survived deletion"
            )
            assert model._default_manager.filter(**{f"{field}_id": other_user.pk}).exists(), (
                f"{model.__name__} rows of another user were removed"
            )

    def test_audit_trail_is_pseudonymized_not_linked(self, auth_client, user, other_user):
        from apps.audit.services import pseudonym

        populate(user)
        populate(other_user)
        user_id = str(user.pk)
        events_before = AuditEvent.objects.filter(actor=user).count()
        assert events_before > 0

        auth_client.delete("/api/v1/account", {"password": DEFAULT_PASSWORD}, format="json")

        kept = AuditEvent.objects.filter(actor_hash=pseudonym(user_id))
        # Every earlier event, plus "deletion requested" and "erased".
        assert kept.count() >= events_before + 1
        assert not kept.exclude(actor__isnull=True).exists()
        assert set(kept.values_list("object_id", flat=True)) == {""}
        dumped = json.dumps(list(kept.values("actor_hash", "object_id", "metadata", "action")))
        assert user_id not in dumped
        assert user.email not in dumped
        assert "account.erased" in dumped
        # Another person's trail is untouched and still linked to them.
        assert AuditEvent.objects.filter(actor=other_user).exists()

    def test_shared_content_survives_account_deletion(self, auth_client, user):
        made = populate(user)
        auth_client.delete("/api/v1/account", {"password": DEFAULT_PASSWORD}, format="json")
        assert type(made["exercise"]).objects.filter(pk=made["exercise"].pk).exists()

    def test_unverified_account_purge_also_removes_owned_rows(self, settings):
        stale = UserFactory(email_verified_at=None)
        populate(stale)
        User.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(days=settings.UNVERIFIED_ACCOUNT_TTL_DAYS + 1)
        )
        services.purge_stale_accounts()
        from apps.checkins.models import CheckIn

        assert not CheckIn.objects.filter(user_id=stale.pk).exists()


class TestFieldEncryption:
    def test_round_trip(self):
        token = fields.encrypt("private words")
        assert "private words" not in token
        assert fields.decrypt(token) == "private words"

    def test_same_text_never_encrypts_to_the_same_value(self):
        assert fields.encrypt("same") != fields.encrypt("same")

    def test_a_different_key_cannot_read_it(self, settings):
        token = fields.encrypt("private words")
        settings.FIELD_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
        with pytest.raises(InvalidToken):
            fields.decrypt(token)

    def test_key_rotation_keeps_old_data_readable(self, settings):
        old_key = settings.FIELD_ENCRYPTION_KEYS[0]
        token = fields.encrypt("written with the old key")
        new_key = Fernet.generate_key().decode()
        settings.FIELD_ENCRYPTION_KEYS = [new_key, old_key]

        assert fields.decrypt(token) == "written with the old key"
        fresh = fields.encrypt("written after rotation")
        settings.FIELD_ENCRYPTION_KEYS = [new_key]
        assert fields.decrypt(fresh) == "written after rotation"

    def test_refuses_to_run_without_a_key(self, settings):
        from django.core.exceptions import ImproperlyConfigured

        settings.FIELD_ENCRYPTION_KEYS = []
        with pytest.raises(ImproperlyConfigured):
            fields.encrypt("anything")

    @pytest.mark.django_db
    def test_empty_values_stay_empty(self, user):
        episode = EpisodeFactory(user=user, what_helped="")
        episode.refresh_from_db()
        assert episode.what_helped == ""
