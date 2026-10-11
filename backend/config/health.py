"""Liveness and readiness probes. They expose component names only, never details."""

from __future__ import annotations

from django.core.cache import cache
from django.db import connection, transaction
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:  # noqa: BLE001 - a probe reports failure, it does not raise
        return False


def _cache_ok() -> bool:
    try:
        cache.set("health:ping", "1", timeout=5)
        return cache.get("health:ping") == "1"
    except Exception:  # noqa: BLE001
        return False


# Probes opt out of the per-request transaction so they answer even when the
# database is down.
@method_decorator(transaction.non_atomic_requests, name="dispatch")
class HealthView(APIView):
    """Liveness: the process is up and can answer a request."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes: list = []

    @extend_schema(
        responses=inline_serializer("Health", {"status": serializers.CharField()}),
        auth=[],
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


@method_decorator(transaction.non_atomic_requests, name="dispatch")
class ReadyView(APIView):
    """Readiness: the database and Redis are reachable."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes: list = []

    @extend_schema(
        responses=inline_serializer(
            "Ready",
            {
                "status": serializers.CharField(),
                "checks": serializers.DictField(child=serializers.BooleanField()),
            },
        ),
        auth=[],
    )
    def get(self, request: Request) -> Response:
        checks = {"database": _database_ok(), "cache": _cache_ok()}
        ready = all(checks.values())
        return Response(
            {"status": "ok" if ready else "unavailable", "checks": checks},
            status=200 if ready else 503,
        )
