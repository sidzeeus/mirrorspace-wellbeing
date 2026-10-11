"""Proves the cross-user contract passes on a scoped endpoint and fails on a leaky one."""

from __future__ import annotations

import pytest
from django.urls import path
from rest_framework import serializers, viewsets

from apps.accounts.models import Profile

from .harness import OwnedResourceContract


class _ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["id", "display_name"]


class _ScopedViewSet(viewsets.ModelViewSet):
    serializer_class = _ProfileSerializer

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user).order_by("id")


class _LeakyViewSet(viewsets.ModelViewSet):
    """The mistake the contract exists to catch: no filter on the signed-in user."""

    serializer_class = _ProfileSerializer
    queryset = Profile.objects.order_by("id")


def _routes(prefix, viewset):
    return [
        path(prefix, viewset.as_view({"get": "list"})),
        path(
            f"{prefix}/<int:pk>",
            viewset.as_view(
                {
                    "get": "retrieve",
                    "put": "update",
                    "patch": "partial_update",
                    "delete": "destroy",
                }
            ),
        ),
    ]


urlpatterns = [*_routes("scoped", _ScopedViewSet), *_routes("leaky", _LeakyViewSet)]


@pytest.mark.django_db
@pytest.mark.urls("tests.test_harness")
class TestScopedEndpointPasses(OwnedResourceContract):
    list_url = "/scoped"
    update_payload = {"display_name": "changed"}

    def make(self, user):
        return user.profile


class _LeakyContract(OwnedResourceContract):
    list_url = "/leaky"
    update_payload = {"display_name": "changed"}

    def make(self, user):
        return user.profile


@pytest.mark.django_db
@pytest.mark.urls("tests.test_harness")
@pytest.mark.parametrize(
    "check",
    [
        "test_list_contains_only_own_objects",
        "test_other_user_cannot_read",
        "test_other_user_cannot_update",
        "test_other_user_cannot_delete",
    ],
)
def test_contract_fails_on_leaky_endpoint(check):
    with pytest.raises(AssertionError):
        getattr(_LeakyContract(), check)()
