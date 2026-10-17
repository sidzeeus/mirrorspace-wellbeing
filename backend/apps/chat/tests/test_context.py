"""Letting Sushi know about the student's own wellbeing (decision B83).

Off by default; the student turns it on, can preview exactly what is shared, and can
turn it off. When on, the AI receives a short summary of their check-ins, sleep,
triggers, recent episodes and their safety plan's warning signs and coping steps.
Never: the people in the safety plan, Vent entries, contacts, name or email.
If a message mentions one of their own triggers, the reply carries their coping steps.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.chat import context, services
from apps.chat.models import ChatContextSetting
from apps.chat.providers import MockProvider, ProviderUnavailable
from apps.safety.models import SafetyPlan
from apps.vent.models import VentEntry
from tests.factories import (
    CheckInFactory,
    EpisodeFactory,
    TriggerFactory,
    TrustedContactFactory,
    UserFactory,
)
from tests.harness import SingletonResourceContract, client_for

pytestmark = pytest.mark.django_db

URL = "/api/v1/chat/context"
CANARY = "CANARY-context-private"


@pytest.fixture(autouse=True)
def _reset():
    MockProvider.reset()
    yield
    MockProvider.reset()


@pytest.fixture
def student():
    user = UserFactory(display_name=f"{CANARY}-name")
    today = timezone.localdate()
    for days, (mood, sleep) in enumerate([(2, "5.0"), (3, "6.5"), (2, "4.5")]):
        CheckInFactory(
            user=user, local_date=today - timedelta(days=days), mood=mood, sleep_hours=sleep
        )
    exams = TriggerFactory(user=user, label="exam results")
    TriggerFactory(user=user, label="arguments with dad")
    TriggerFactory(user=user, label="old archived thing", is_active=False)
    EpisodeFactory(user=user, trigger=exams, intensity=4, what_helped="walking outside")
    SafetyPlan.objects.create(
        user=user,
        warning_signs=["can't stop overthinking"],
        coping_steps=["slow breathing", "text my sister"],
        people=[f"{CANARY}-person-in-plan"],
    )
    TrustedContactFactory(user=user, name=f"{CANARY}-contact")
    VentEntry.objects.create(user=user, body=f"{CANARY}-vent")
    return user


def enable(user):
    ChatContextSetting.objects.update_or_create(user=user, defaults={"enabled": True})


class TestChatContextIsolation(SingletonResourceContract):
    url = URL
    payload = {"enabled": True}


class TestOffByDefault:
    def test_nothing_personal_reaches_the_model_until_turned_on(self, student):
        services.generate_reply(student, "hi, how are you")
        sent = json.dumps(MockProvider.calls[0])
        for private in ("exam results", "slow breathing", "walking outside", "overthinking"):
            assert private not in sent
        assert services.generate_reply(student, "exam results again").plan is None

    def test_setting_is_off_for_a_new_account(self, student):
        body = client_for(student).get(URL).json()
        assert body["enabled"] is False


class TestWhatIsShared:
    def test_summary_includes_the_chosen_categories(self, student):
        text = context.build_context(student)
        assert "Check-ins in the last 14 days: 3" in text
        assert "sleep" in text.lower()
        assert "exam results" in text and "arguments with dad" in text
        assert "old archived thing" not in text
        assert "walking outside" in text
        assert "can't stop overthinking" in text
        assert "slow breathing" in text and "text my sister" in text

    def test_summary_never_includes_people_vent_contacts_or_identity(self, student):
        text = context.build_context(student)
        assert CANARY not in text
        assert student.email not in text

    def test_the_model_receives_the_summary_only_when_on(self, student):
        enable(student)
        services.generate_reply(student, "hello")
        system = MockProvider.calls[0]["system"]
        assert "slow breathing" in system
        assert CANARY not in json.dumps(MockProvider.calls[0])

    def test_preview_is_exactly_what_the_model_would_see(self, student):
        enable(student)
        preview = client_for(student).get(URL).json()["preview"]
        services.generate_reply(student, "hello")
        assert preview in MockProvider.calls[0]["system"]

    def test_turning_it_off_stops_sharing_at_once(self, student):
        client = client_for(student)
        assert client.put(URL, {"enabled": True}, format="json").json()["enabled"] is True
        assert client.put(URL, {"enabled": False}, format="json").json()["enabled"] is False
        services.generate_reply(student, "hello")
        assert "slow breathing" not in MockProvider.calls[0]["system"]

    def test_turning_it_on_and_off_is_recorded_without_content(self, student):
        client = client_for(student)
        client.put(URL, {"enabled": True}, format="json")
        client.put(URL, {"enabled": False}, format="json")
        actions = list(AuditEvent.objects.values_list("action", flat=True))
        assert "chat.context_enabled" in actions and "chat.context_disabled" in actions
        assert "slow breathing" not in json.dumps(list(AuditEvent.objects.values()), default=str)


class TestTriggerMatching:
    @pytest.mark.parametrize(
        "message",
        ["my EXAM RESULTS come out tomorrow", "ugh, arguments with dad again", "Exam results..."],
    )
    def test_mentioning_a_trigger_brings_the_safety_plan(self, student, message):
        enable(student)
        reply = services.generate_reply(student, message)
        assert reply.plan is not None
        assert reply.plan["coping_steps"] == ["slow breathing", "text my sister"]
        assert reply.plan["matched"]
        assert "trigger list" in MockProvider.calls[0]["system"]

    def test_unrelated_or_archived_words_do_not_match(self, student):
        enable(student)
        for message in ["I like dad jokes", "results of the match", "old archived thing"]:
            assert services.generate_reply(student, message).plan is None

    def test_the_plan_still_appears_when_the_ai_is_down(self, student):
        enable(student)
        MockProvider.script = ProviderUnavailable()
        reply = services.generate_reply(student, "exam results tomorrow")
        assert reply.kind == services.UNAVAILABLE
        assert reply.plan is not None

    def test_crisis_wording_still_gets_the_fixed_reply_and_alerts_nobody(self, student):
        from apps.notifications.models import Notification

        enable(student)
        reply = services.generate_reply(student, "exam results tomorrow and I want to kill myself")
        assert reply.kind == services.SAFETY
        assert MockProvider.calls == []
        assert not Notification.objects.exists()

    def test_the_api_returns_the_plan_card(self, student):
        enable(student)
        client = client_for(student)
        session = client.post("/api/v1/chat/sessions", {}, format="json").json()
        body = client.post(
            f"/api/v1/chat/sessions/{session['id']}/messages",
            {"text": "exam results are making me spiral"},
            format="json",
        ).json()
        assert body["plan"]["coping_steps"] == ["slow breathing", "text my sister"]


def test_nothing_private_is_logged(student, caplog):
    caplog.set_level(logging.DEBUG)
    enable(student)
    client = client_for(student)
    client.get(URL)
    services.generate_reply(student, "exam results tomorrow")
    logged = "\n".join(
        f"{r.getMessage()} {json.dumps(r.__dict__, default=str)}" for r in caplog.records
    )
    for private in ("exam results", "slow breathing", "overthinking", "walking outside"):
        assert private not in logged


def test_the_setting_is_exported_and_erased(student):
    from apps.accounts.export import build_export
    from apps.accounts.services import _erase

    enable(student)
    assert build_export(student)["chat_context"]["enabled"] is True
    _erase(student)
    assert not ChatContextSetting.objects.exists()
