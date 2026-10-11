from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import SimpleRouter

from apps.accounts.views import AccountView, ExportView
from apps.checkins.views import CheckInViewSet, PatternsView
from apps.episodes.views import EpisodeViewSet, TriggerViewSet
from apps.wellbeing.views import ExerciseEventViewSet, ExerciseViewSet
from config import schema  # noqa: F401 - registers the OpenAPI auth scheme
from config.health import HealthView, ReadyView

router = SimpleRouter(trailing_slash=False)
router.register("check-ins", CheckInViewSet, basename="check-in")
router.register("episodes", EpisodeViewSet, basename="episode")
router.register("triggers", TriggerViewSet, basename="trigger")
router.register("exercises", ExerciseViewSet, basename="exercise")
router.register("exercise-events", ExerciseEventViewSet, basename="exercise-event")

api_v1: list[URLPattern | URLResolver] = [
    path("health", HealthView.as_view(), name="health"),
    path("ready", ReadyView.as_view(), name="ready"),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("auth/", include("apps.accounts.urls")),
    path("account", AccountView.as_view(), name="account"),
    path("export", ExportView.as_view(), name="export"),
    path("patterns", PatternsView.as_view(), name="patterns"),
    *router.urls,
]

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", include(api_v1)),
]
