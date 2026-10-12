from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from config.views import OwnedModelViewSet

from . import policy, services
from .models import MAX_RETENTION_DAYS, ChatFeedback, ChatMessage, ChatSession


class ChatThrottle(UserRateThrottle):
    scope = "chat"


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "kind", "content", "sources", "created_at"]
        read_only_fields = fields


class ChatSessionSerializer(serializers.ModelSerializer):
    retention_days = serializers.IntegerField(
        min_value=1, max_value=MAX_RETENTION_DAYS, required=False
    )
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ["id", "save_transcript", "retention_days", "expires_at", "created_at", "messages"]
        read_only_fields = ["id", "expires_at", "created_at", "messages"]


class TurnSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=4000)


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=services.MAX_MESSAGE_LENGTH, trim_whitespace=True)
    # Earlier turns, held by the browser when transcripts are off. Ignored when on.
    history = serializers.ListField(child=TurnSerializer(), required=False, max_length=20)


class FeedbackSerializer(serializers.ModelSerializer):
    session = serializers.PrimaryKeyRelatedField(
        queryset=ChatSession.objects.none(), required=False, allow_null=True
    )
    kind = serializers.ChoiceField(
        choices=[
            services.ANSWER,
            services.SAFETY,
            services.UNSUPPORTED,
            services.UNAVAILABLE,
            services.LIMIT,
            services.OFF_POLICY,
        ]
    )

    class Meta:
        model = ChatFeedback
        fields = ["id", "session", "kind", "helpful", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            fields["session"].queryset = ChatSession.objects.filter(user=request.user)  # type: ignore[attr-defined]
        return fields


class ChatSessionViewSet(OwnedModelViewSet):
    """A student's own conversations. Nothing is saved unless they turn saving on."""

    model = ChatSession
    serializer_class = ChatSessionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[ChatSession]:
        return super().get_queryset().prefetch_related("messages").order_by("-created_at")

    def get_throttles(self) -> list[Any]:
        if self.action == "messages":
            return [ChatThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer: serializers.BaseSerializer[Any]) -> None:
        session = serializer.save(user=self.request.user)
        if session.save_transcript:
            services.set_transcript(session, save=True)

    def perform_update(self, serializer: serializers.BaseSerializer[Any]) -> None:
        session = cast(ChatSession, serializer.instance)
        data = serializer.validated_data
        services.set_transcript(
            session,
            save=data.get("save_transcript", session.save_transcript),
            retention_days=data.get("retention_days"),
        )

    @extend_schema(request=SendMessageSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"])
    def messages(self, request: Request, pk: str | None = None) -> Response:
        """Send one message and get one reply. See apps/chat/services.py for the steps."""
        session = self.get_object()
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = services.respond(
            session,
            serializer.validated_data["text"],
            serializer.validated_data.get("history"),
        )
        return Response(asdict(reply))


class ChatFeedbackViewSet(OwnedModelViewSet):
    model = ChatFeedback
    serializer_class = FeedbackSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]


class ChatInfoView(APIView):
    """GET /api/v1/chat/info: what the chat is and is not, shown before the first message."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, auth=[])
    def get(self, request: Request) -> Response:
        return Response(
            {
                "disclosure": policy.DISCLOSURE,
                "max_message_length": services.MAX_MESSAGE_LENGTH,
                "max_retention_days": MAX_RETENTION_DAYS,
                "transcripts_saved_by_default": False,
                "signed_in": request.user.is_authenticated,
            },
            status=status.HTTP_200_OK,
        )
