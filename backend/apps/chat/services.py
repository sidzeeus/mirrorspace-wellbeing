"""The chat pipeline. The order of the steps is the safety design.

    1. Safety check on the student's message      (code, before any model)
    2. Usage budgets                                (per student, and for everyone)
    3. Retrieval of reviewed passages               (offered to the model when they match)
    4. The AI provider                              (failure -> fixed reply)
    5. Safety and policy check on the model's reply (code, after the model)

A message that suggests a crisis is answered at step 1 with a fixed reply. It is never
sent to the provider, and it is answered even when the budget is used up or the
provider is down. Nothing in this module contacts anyone.

Nothing here logs a message or a reply: only identifiers and the kind of outcome.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import F, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record as audit

from . import policy, safety
from .knowledge import Passage, retrieve
from .models import ChatMessage, ChatSession, ChatUsage, MessageRole
from .providers import ProviderRefused, ProviderUnavailable, get_provider

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_TURNS = 20

ANSWER = "answer"
SAFETY = "safety"
UNSUPPORTED = "unsupported"
UNAVAILABLE = "unavailable"
LIMIT = "limit"
OFF_POLICY = "off_policy"


@dataclass(frozen=True)
class Reply:
    kind: str
    text: str
    sources: list[dict[str, str]] = field(default_factory=list)
    actions: list[dict[str, str]] = field(default_factory=list)
    # Set only for safety replies: "crisis" or "distress". Returned to the screen so it
    # can show the right options. Never stored.
    level: str | None = None

    @property
    def from_ai(self) -> bool:
        return self.kind == ANSWER


def _safety_reply(level: str) -> Reply:
    return Reply(SAFETY, safety.FIXED_REPLIES[level], actions=list(safety.ACTIONS), level=level)


def _budget_left(user: User) -> bool:
    today = timezone.localdate()
    used = ChatUsage.objects.filter(user=user, day=today).values_list("replies", flat=True).first()
    if (used or 0) >= settings.CHAT_USER_DAILY_LIMIT:
        return False
    everyone = ChatUsage.objects.filter(day=today).aggregate(total=Sum("replies"))["total"] or 0
    return everyone < settings.CHAT_GLOBAL_DAILY_LIMIT


def _count_reply(user: User) -> None:
    usage, _ = ChatUsage.objects.get_or_create(user=user, day=timezone.localdate())
    ChatUsage.objects.filter(pk=usage.pk).update(replies=F("replies") + 1)


def _sources(passages: list[Passage]) -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    for passage in passages:
        seen.setdefault(passage.slug, {"title": passage.title, "source": passage.source})
    return list(seen.values())


def _clean_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Recent turns sent by the browser, bounded and reduced to plain text."""
    turns = []
    for item in history[-MAX_HISTORY_TURNS:]:
        role, content = item.get("role"), item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            turns.append({"role": role, "content": content[:MAX_MESSAGE_LENGTH]})
    # The provider needs the conversation to start with the student.
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return turns


def generate_reply(user: User, text: str, history: list[dict[str, Any]] | None = None) -> Reply:
    # 1. Safety first, in code, before anything else can fail or refuse.
    assessment = safety.assess(text)
    if assessment.level is not None:
        logger.info("chat_safety_reply_shown", extra={"user_id": str(user.pk)})
        audit("chat.safety_reply_shown", user=user)
        return _safety_reply(assessment.level)

    # 2. Budgets.
    if not _budget_left(user):
        return Reply(LIMIT, policy.LIMIT_REPLY)

    # 3. Reviewed material, when some matches. The model may also simply talk (B74).
    passages = retrieve(text, user.preferred_language)

    # 4. The provider gets instructions, passages and conversation text. Nothing else.
    messages = [*_clean_history(history or []), {"role": "user", "content": text}]
    try:
        answer = get_provider().complete(
            system=policy.build_system_prompt(passages), messages=messages
        )
    except ProviderRefused:
        return Reply(OFF_POLICY, policy.OFF_POLICY_REPLY)
    except ProviderUnavailable:
        logger.warning("chat_provider_unavailable")
        return Reply(UNAVAILABLE, policy.UNAVAILABLE_REPLY)
    _count_reply(user)

    # 5. Check what came back. The model's reply is not trusted either.
    after = safety.assess(answer)
    if after.level == safety.CRISIS:
        audit("chat.safety_reply_shown", user=user)
        return _safety_reply(safety.CRISIS)
    if policy.violates_policy(answer):
        logger.warning("chat_reply_blocked_by_policy")
        return Reply(OFF_POLICY, policy.OFF_POLICY_REPLY)
    return Reply(ANSWER, answer, sources=_sources(passages))


def respond(session: ChatSession, text: str, history: list[dict[str, Any]] | None = None) -> Reply:
    """Answer one message, saving the exchange only if the student turned saving on."""
    saved_history: list[dict[str, Any]] | None = history
    if session.save_transcript:
        saved_history = [
            {"role": "user" if m.role == MessageRole.USER else "assistant", "content": m.content}
            for m in session.messages.order_by("-created_at")[:MAX_HISTORY_TURNS][::-1]
        ]
    reply = generate_reply(session.user, text, saved_history)
    if session.save_transcript:
        ChatMessage.objects.create(session=session, role=MessageRole.USER, content=text)
        ChatMessage.objects.create(
            session=session,
            role=MessageRole.ASSISTANT if reply.from_ai else MessageRole.FIXED,
            kind=reply.kind,
            content=reply.text,
            sources=reply.sources,
        )
    return reply


def set_transcript(session: ChatSession, *, save: bool, retention_days: int | None = None) -> None:
    """Turn saving on or off. Turning it off deletes what was saved."""
    if retention_days is not None:
        session.retention_days = retention_days
    session.save_transcript = save
    session.expires_at = timezone.now() + timedelta(days=session.retention_days) if save else None
    session.save(update_fields=["save_transcript", "retention_days", "expires_at"])
    if save:
        audit("chat.transcript_enabled", user=session.user, obj=session)
    else:
        session.messages.all().delete()
        audit("chat.transcript_deleted", user=session.user, obj=session)


def purge_expired() -> int:
    """Delete saved conversations past their retention date, and old empty sessions."""
    now = timezone.now()
    expired, _ = ChatSession.objects.filter(save_transcript=True, expires_at__lt=now).delete()
    stale, _ = ChatSession.objects.filter(
        save_transcript=False, created_at__lt=now - timedelta(days=1)
    ).delete()
    ChatUsage.objects.filter(day__lt=timezone.localdate() - timedelta(days=30)).delete()
    logger.info("chat_purged", extra={"count": expired + stale})
    return expired + stale
