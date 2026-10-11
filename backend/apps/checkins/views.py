from __future__ import annotations

from datetime import date
from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from config.views import OwnedModelViewSet

from .dates import local_today, user_zone
from .models import METRIC_FIELDS, CheckIn
from .patterns import MAX_DAYS, MIN_DAYS, build_patterns, clamp_days
from .serializers import CheckInSerializer


def _parse_date(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


@extend_schema_view(
    list=extend_schema(
        parameters=[OpenApiParameter("from", str), OpenApiParameter("to", str)],
    ),
    create=extend_schema(responses={200: CheckInSerializer, 201: CheckInSerializer}),
)
class CheckInViewSet(OwnedModelViewSet):
    model = CheckIn
    serializer_class = CheckInSerializer

    def get_queryset(self) -> QuerySet[CheckIn]:
        queryset = super().get_queryset().order_by("-local_date")
        if self.action == "list":
            start = _parse_date(self.request.query_params.get("from"))
            end = _parse_date(self.request.query_params.get("to"))
            if start:
                queryset = queryset.filter(local_date__gte=start)
            if end:
                queryset = queryset.filter(local_date__lte=end)
        return queryset

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Save the check-in for a day. Sending the same day again replaces it.

        There is one check-in per local day, so a repeat is an update rather than an
        error: 201 when the day is new, 200 when it already existed.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = cast(User, request.user)
        data = dict(serializer.validated_data)
        local_date = data.pop("local_date", None) or local_today(user)
        defaults = {field: data.get(field) for field in METRIC_FIELDS}
        defaults["timezone"] = user_zone(user).key
        check_in, created = CheckIn.objects.update_or_create(
            user=user, local_date=local_date, defaults=defaults
        )
        return Response(
            self.get_serializer(check_in).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PatternsView(APIView):
    """GET /api/v1/patterns: descriptive summaries of the person's own check-ins."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "days", int, description=f"Length of the period, {MIN_DAYS} to {MAX_DAYS}."
            )
        ],
        responses=inline_serializer(
            "Patterns",
            {
                "range": serializers.DictField(),
                "check_in_days": serializers.IntegerField(),
                "series": serializers.ListField(child=serializers.DictField()),
                "weekly": serializers.ListField(child=serializers.DictField()),
                "observations": serializers.ListField(child=serializers.DictField()),
                "note": serializers.CharField(),
            },
        ),
    )
    def get(self, request: Request) -> Response:
        days = clamp_days(request.query_params.get("days"))
        return Response(build_patterns(cast(User, request.user), days))
