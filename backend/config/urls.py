from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView

from apps.accounts.views import AccountView
from config import schema  # noqa: F401 - registers the OpenAPI auth scheme
from config.health import HealthView, ReadyView

api_v1: list[URLPattern | URLResolver] = [
    path("health", HealthView.as_view(), name="health"),
    path("ready", ReadyView.as_view(), name="ready"),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("auth/", include("apps.accounts.urls")),
    path("account", AccountView.as_view(), name="account"),
]

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", include(api_v1)),
]
