from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from apps.wellbeing.models import ReviewStatus, visible_statuses
from config.fields import EncryptedTextField

# Size of the vectors produced by the local embedder in `knowledge.py`. Changing the
# embedder means a migration for this column and re-running `index_knowledge`.
EMBEDDING_DIMENSIONS = 256

MAX_RETENTION_DAYS = 30


class ContentDocument(models.Model):
    """A reviewed piece of educational text the chat may quote from.

    Only documents approved by a qualified reviewer are indexed and retrieved
    (non-negotiable 8). Nothing a student writes is ever stored here.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    # Where the text comes from: a citation or the reviewer's organisation.
    source = models.CharField(max_length=300)
    audience = models.CharField(max_length=80, default="students aged 18 and over")
    language = models.CharField(max_length=8, choices=settings.LANGUAGES, default="en")
    body = models.TextField()
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    reviewed_on = models.DateField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=120, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.slug


class ChunkQuerySet(models.QuerySet["ContentChunk"]):
    def retrievable(self) -> ChunkQuerySet:
        return self.filter(document__review_status__in=visible_statuses())


class ContentChunk(models.Model):
    """One passage of a document with its embedding, for retrieval."""

    document = models.ForeignKey(ContentDocument, on_delete=models.CASCADE, related_name="chunks")
    position = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    objects = ChunkQuerySet.as_manager()

    class Meta:
        ordering = ["document", "position"]
        constraints = [
            models.UniqueConstraint(fields=["document", "position"], name="chat_chunk_position")
        ]

    def __str__(self) -> str:
        return f"{self.document.slug}#{self.position}"


class ChatSession(models.Model):
    """A conversation. By default it leaves no transcript at all.

    With `save_transcript` off (the default) no message is written to the database:
    the browser holds the conversation and it is gone when the tab closes. A student
    can turn saving on, for at most 30 days, and delete it at any time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    save_transcript = models.BooleanField(default=False)
    retention_days = models.PositiveSmallIntegerField(default=MAX_RETENTION_DAYS)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(retention_days__gte=1, retention_days__lte=MAX_RETENTION_DAYS),
                name="chat_session_retention_range",
            )
        ]

    def __str__(self) -> str:
        return f"chat_session:{self.pk}"


class MessageRole(models.TextChoices):
    USER = "user", "Student"
    ASSISTANT = "assistant", "AI reply"
    FIXED = "fixed", "Fixed, non-AI reply"


class ChatMessage(models.Model):
    """A saved message. Exists only while its session has transcripts turned on."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=MessageRole.choices)
    kind = models.CharField(max_length=20, default="answer")
    content = EncryptedTextField()
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"chat_message:{self.pk}"


class ChatFeedback(models.Model):
    """A thumbs up or down on a reply. A rating only: there is no text field."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_feedback"
    )
    session = models.ForeignKey(
        ChatSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="feedback"
    )
    kind = models.CharField(max_length=20)
    helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"chat_feedback:{self.pk}"


class ChatUsage(models.Model):
    """How many AI replies a student used on one day. A count, for the budget."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_usage"
    )
    day = models.DateField()
    replies = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="chat_usage_per_day")]

    def __str__(self) -> str:
        return f"chat_usage:{self.pk}"


class ChatContextSetting(models.Model):
    """Whether the student lets Sushi see a summary of their own records (B83).

    Off unless the student turns it on. See apps/chat/context.py for what is shared.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_context"
    )
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"ChatContextSetting {self.pk}"
