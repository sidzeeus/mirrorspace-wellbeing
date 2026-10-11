"""View base classes shared by the apps."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import viewsets
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView


@method_decorator(csrf_protect, name="dispatch")
class CsrfProtectedAPIView(APIView):
    """Enforces CSRF even for anonymous requests.

    DRF only checks CSRF once a session exists. Sign-in, registration and the
    email-link endpoints are called anonymously, so they opt in here.
    """


class OwnedModelViewSet(viewsets.ModelViewSet):
    """CRUD for rows that belong to one student.

    Non-negotiable 7: every query is filtered by the signed-in user, so another
    person's row is simply not found (404), and the owner is always set by the server,
    never taken from the request body.
    """

    #: The model served. It must have a `user` foreign key.
    model: type[models.Model]

    def get_queryset(self) -> models.QuerySet[Any]:
        if getattr(self, "swagger_fake_view", False):
            # Schema generation has no signed-in user; it only needs the model.
            return self.model._default_manager.none()
        return self.model._default_manager.filter(user=self.request.user)

    def perform_create(self, serializer: BaseSerializer[Any]) -> None:
        serializer.save(user=self.request.user)
