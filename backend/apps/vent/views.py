from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from config.views import OwnedModelViewSet

from .models import MAX_LENGTH, VentEntry
from .reactions import react


class VentThrottle(UserRateThrottle):
    scope = "vent"


class VentEntrySerializer(serializers.ModelSerializer):
    body = serializers.CharField(max_length=MAX_LENGTH, trim_whitespace=True)

    class Meta:
        model = VentEntry
        fields = ["id", "body", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReflectSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=MAX_LENGTH, trim_whitespace=True)


class VentEntryViewSet(OwnedModelViewSet):
    """Entries the student chose to keep. They can be read and deleted, not edited."""

    model = VentEntry
    serializer_class = VentEntrySerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[VentEntry]:
        return super().get_queryset().order_by("-created_at")


class VentReflectView(APIView):
    """How the figure reacts to what was written. Stores and logs nothing."""

    throttle_classes = [VentThrottle]

    @extend_schema(request=ReflectSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request: Request) -> Response:
        serializer = ReflectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reaction = react(serializer.validated_data["text"])
        body: dict[str, Any] = {"reaction": reaction.kind, "level": reaction.level}
        return Response(body)
