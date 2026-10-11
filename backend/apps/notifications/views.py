from __future__ import annotations

import hmac

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.views import OwnedModelViewSet

from . import services
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Delivery status only. There is no message text here by design."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "purpose",
            "contact",
            "status",
            "status_code",
            "scheduled_at",
            "sent_at",
        ]
        read_only_fields = fields


class NotificationViewSet(OwnedModelViewSet):
    """What was sent on the student's behalf, and what happened to it.

    "sent" means the email provider accepted the message. It never means the message
    was delivered to an inbox or read.
    """

    model = Notification
    serializer_class = NotificationSerializer
    http_method_names = ["get", "head", "options"]


class ProviderEventSerializer(serializers.Serializer):
    provider_reference = serializers.CharField(max_length=255)
    event = serializers.ChoiceField(choices=["bounced", "complained"])


class EmailWebhookView(APIView):
    """POST /api/v1/webhooks/email-events: bounces and complaints from the provider.

    Authenticated by a shared secret header. Disabled (404) unless EMAIL_WEBHOOK_SECRET
    is set. The body carries a message reference and an event type, never an address.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes: list = []

    @extend_schema(request=ProviderEventSerializer, responses={200: OpenApiTypes.OBJECT}, auth=[])
    def post(self, request: Request) -> Response:
        secret = settings.EMAIL_WEBHOOK_SECRET
        if not secret:
            return Response(status=status.HTTP_404_NOT_FOUND)
        supplied = request.headers.get("X-Webhook-Secret", "")
        if not hmac.compare_digest(supplied.encode(), secret.encode()):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ProviderEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handled = services.handle_provider_event(**serializer.validated_data)
        return Response({"handled": handled})
