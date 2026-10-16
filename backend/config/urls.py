from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import SimpleRouter

from apps.accounts.views import AccountView, ExportView
from apps.chat.views import ChatFeedbackViewSet, ChatInfoView, ChatSessionViewSet
from apps.checkins.views import CheckInViewSet, PatternsView
from apps.episodes.views import EpisodeViewSet, TriggerViewSet
from apps.notifications.views import EmailWebhookView, NotificationViewSet
from apps.safety.views import ResourceViewSet, SafetyPlanView
from apps.sharing import views as sharing
from apps.vent.views import VentEntryViewSet, VentReflectView
from apps.wellbeing.views import ExerciseEventViewSet, ExerciseViewSet
from config import schema  # noqa: F401 - registers the OpenAPI auth scheme
from config.health import HealthView, ReadyView

router = SimpleRouter(trailing_slash=False)
router.register("check-ins", CheckInViewSet, basename="check-in")
router.register("episodes", EpisodeViewSet, basename="episode")
router.register("triggers", TriggerViewSet, basename="trigger")
router.register("exercises", ExerciseViewSet, basename="exercise")
router.register("exercise-events", ExerciseEventViewSet, basename="exercise-event")
router.register("resources", ResourceViewSet, basename="resource")
router.register("trusted-contacts", sharing.TrustedContactViewSet, basename="trusted-contact")
router.register("sharing/consent", sharing.ConsentViewSet, basename="consent")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("chat/sessions", ChatSessionViewSet, basename="chat-session")
router.register("chat/feedback", ChatFeedbackViewSet, basename="chat-feedback")
router.register("vent-entries", VentEntryViewSet, basename="vent-entry")

api_v1: list[URLPattern | URLResolver] = [
    path("health", HealthView.as_view(), name="health"),
    path("ready", ReadyView.as_view(), name="ready"),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("auth/", include("apps.accounts.urls")),
    path("account", AccountView.as_view(), name="account"),
    path("export", ExportView.as_view(), name="export"),
    path("patterns", PatternsView.as_view(), name="patterns"),
    path("chat/info", ChatInfoView.as_view(), name="chat-info"),
    path("vent/reflect", VentReflectView.as_view(), name="vent-reflect"),
    path("safety-plan", SafetyPlanView.as_view(), name="safety-plan"),
    path("sharing/preview", sharing.WeeklyPreviewView.as_view(), name="sharing-preview"),
    path("sharing/notices", sharing.NoticeVersionsView.as_view(), name="sharing-notices"),
    path("sos/preview", sharing.SosPreviewView.as_view(), name="sos-preview"),
    path("sos/notify-contact", sharing.SosNotifyContactView.as_view(), name="sos-notify-contact"),
    path("contact-invitations/view", sharing.InvitationView.as_view(), name="invitation-view"),
    path(
        "contact-invitations/accept",
        sharing.InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
    path(
        "contact-invitations/decline",
        sharing.InvitationDeclineView.as_view(),
        name="invitation-decline",
    ),
    path("unsubscribe", sharing.UnsubscribeView.as_view(), name="unsubscribe"),
    path(
        "unsubscribe/one-click",
        sharing.OneClickUnsubscribeView.as_view(),
        name="unsubscribe-one-click",
    ),
    path("webhooks/email-events", EmailWebhookView.as_view(), name="webhook-email-events"),
    *router.urls,
]

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/", include(api_v1)),
]
