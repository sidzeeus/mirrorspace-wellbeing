from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.db.models import OuterRef, Q, QuerySet, Subquery
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets

from apps.accounts.models import User
from config.views import OwnedModelViewSet

from .models import (
    Exercise,
    ExerciseCategory,
    ExerciseEvent,
    ExerciseEventKind,
    visible_statuses,
)
from .serializers import ExerciseEventSerializer, ExerciseSerializer

_LANGUAGES = [code for code, _ in settings.LANGUAGES]


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("category", str, enum=ExerciseCategory.values),
            OpenApiParameter("lang", str, enum=_LANGUAGES),
            OpenApiParameter("include_hidden", bool),
        ]
    )
)
class ExerciseViewSet(viewsets.ReadOnlyModelViewSet):
    """Browse reviewed exercises. Content is shared; nothing here is personal."""

    serializer_class = ExerciseSerializer
    queryset = Exercise.objects.none()

    def _language(self) -> str:
        requested = self.request.query_params.get("lang")
        if requested in _LANGUAGES:
            return requested
        return getattr(self.request.user, "preferred_language", settings.LANGUAGE_CODE)

    def get_queryset(self) -> QuerySet[Exercise]:
        language = self._language()
        latest_hide = (
            ExerciseEvent.objects.filter(
                user=cast(User, self.request.user),
                exercise=OuterRef("pk"),
                kind__in=[ExerciseEventKind.HIDDEN, ExerciseEventKind.UNHIDDEN],
            )
            .order_by("-created_at")
            .values("kind")[:1]
        )
        queryset = (
            Exercise.objects.visible()
            .filter(
                translations__language__in={language, settings.LANGUAGE_CODE},
                translations__review_status__in=visible_statuses(),
            )
            .distinct()
            .annotate(hide_state=Subquery(latest_hide))
            .prefetch_related("translations")
            .order_by("category", "slug")
        )
        category = self.request.query_params.get("category")
        if category in ExerciseCategory.values:
            queryset = queryset.filter(category=category)
        if self.action == "list" and self.request.query_params.get("include_hidden") != "true":
            # Not `.exclude(hide_state=HIDDEN)`: in SQL that also drops rows where the
            # annotation is NULL, which is every exercise the person never hid.
            queryset = queryset.filter(
                Q(hide_state__isnull=True) | Q(hide_state=ExerciseEventKind.UNHIDDEN)
            )
        return queryset

    def get_serializer_context(self) -> dict[str, Any]:
        return {**super().get_serializer_context(), "language": self._language()}


class ExerciseEventViewSet(OwnedModelViewSet):
    """A student's own optional feedback: completed, helpful, not helpful, hide, show."""

    model = ExerciseEvent
    serializer_class = ExerciseEventSerializer
    # Feedback is added or removed, never edited.
    http_method_names = ["get", "post", "delete", "head", "options"]
