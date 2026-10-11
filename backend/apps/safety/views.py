from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import Resource, ResourceType, SafetyPlan
from .serializers import ResourceSerializer, SafetyPlanSerializer

EMPTY_PLAN: dict[str, Any] = {
    "warning_signs": [],
    "coping_steps": [],
    "people": [],
    "resource_ids": [],
    "updated_at": None,
}


class SafetyPlanView(APIView):
    """GET, PUT, DELETE /api/v1/safety-plan: the signed-in person's own plan.

    There is no id in the URL: the plan is always looked up from the session, so
    there is nothing to tamper with.
    """

    def _plan(self, request: Request) -> SafetyPlan | None:
        return (
            SafetyPlan.objects.filter(user=cast(User, request.user))
            .prefetch_related("resources")
            .first()
        )

    @extend_schema(responses=SafetyPlanSerializer)
    def get(self, request: Request) -> Response:
        plan = self._plan(request)
        if plan is None:
            # Nothing is stored until the person writes something.
            return Response(EMPTY_PLAN)
        return Response(SafetyPlanSerializer(plan).data)

    @extend_schema(request=SafetyPlanSerializer, responses=SafetyPlanSerializer)
    def put(self, request: Request) -> Response:
        plan = self._plan(request)
        serializer = SafetyPlanSerializer(plan, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data)

    @extend_schema(responses={204: None})
    def delete(self, request: Request) -> Response:
        SafetyPlan.objects.filter(user=cast(User, request.user)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        auth=[],
        parameters=[
            OpenApiParameter("region", str, description='Country code, for example "IN".'),
            OpenApiParameter("language", str),
            OpenApiParameter("type", str, enum=ResourceType.values),
        ],
    ),
    retrieve=extend_schema(auth=[]),
)
class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    """Verified helplines and services. Public: shown before sign-up and cached offline.

    Only entries a named person has verified are returned. Each carries its
    verification date and a `stale` flag so an old entry is visibly marked.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = ResourceSerializer
    queryset = Resource.objects.none()

    def get_queryset(self) -> QuerySet[Resource]:
        queryset = Resource.objects.visible().order_by("region", "type", "name")
        params = self.request.query_params
        if region := params.get("region"):
            # "IN" also matches entries for a state such as "IN-KA".
            queryset = queryset.filter(region__istartswith=region[:10])
        if (resource_type := params.get("type")) in ResourceType.values:
            queryset = queryset.filter(type=resource_type)
        if language := params.get("language"):
            queryset = queryset.filter(languages__contains=[language[:8]])
        return queryset
