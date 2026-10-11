from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from config.views import OwnedModelViewSet

from .models import Episode, Trigger
from .serializers import EpisodeSerializer, TriggerSerializer


@extend_schema_view(
    list=extend_schema(parameters=[OpenApiParameter("include_archived", bool)]),
)
class TriggerViewSet(OwnedModelViewSet):
    model = Trigger
    serializer_class = TriggerSerializer

    def get_queryset(self) -> QuerySet[Trigger]:
        queryset = super().get_queryset().prefetch_related("preferred_exercises")
        if self.action == "list" and self.request.query_params.get("include_archived") != "true":
            queryset = queryset.filter(is_active=True)
        return queryset.order_by("created_at")


class EpisodeViewSet(OwnedModelViewSet):
    model = Episode
    serializer_class = EpisodeSerializer

    def get_queryset(self) -> QuerySet[Episode]:
        return super().get_queryset().order_by("-occurred_at")
