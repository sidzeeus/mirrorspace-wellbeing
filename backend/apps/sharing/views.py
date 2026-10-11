from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.checkins.dates import user_zone
from config.views import CsrfProtectedAPIView, OwnedModelViewSet

from . import services, sos
from .models import ConsentPurpose, ConsentRecord, ContactStatus, TrustedContact
from .notices import (
    PRIVACY_NOTICE_VERSION,
    UNSUBSCRIBE_PREVIEW_LINE,
    WEEKLY_NOTICE,
    WEEKLY_NOTICE_VERSION,
)
from .schedule import DEFAULT_HOUR, DEFAULT_WEEKDAY
from .serializers import (
    ConsentCreateSerializer,
    ConsentSerializer,
    ContactTokenSerializer,
    SosPreviewSerializer,
    SosSendSerializer,
    TrustedContactSerializer,
    TrustedContactUpdateSerializer,
    UnsubscribeSerializer,
)
from .throttles import ContactAddThrottle, PublicTokenThrottle, SosThrottle
from .tokens import INVITE, UNSUBSCRIBE, contact_from_token
from .weekly import (
    ALLOWED_FIELDS,
    collect_weekly_fields,
    covered_week,
    render_weekly,
    weekly_format_hash,
)

BAD_LINK = {"detail": "This link is not valid or has expired.", "code": "invalid_link"}


def _own_contact(user: User, contact_id: Any) -> TrustedContact:
    """One of the student's own contacts, or the same error as an unknown id."""
    try:
        contact = TrustedContact.objects.filter(user=user, pk=contact_id).first()
    except (ValueError, DjangoValidationError):
        contact = None  # not a UUID at all
    if contact is None:
        raise services.fail("Choose one of your own trusted contacts.", "invalid_contact")
    return contact


class TrustedContactViewSet(OwnedModelViewSet):
    model = TrustedContact
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "partial_update":
            return TrustedContactUpdateSerializer
        return TrustedContactSerializer

    def get_throttles(self) -> list[Any]:
        if self.action in ("create", "resend_invitation"):
            return [ContactAddThrottle()]
        return super().get_throttles()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = TrustedContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = services.add_contact(cast(User, request.user), **serializer.validated_data)
        return Response(TrustedContactSerializer(contact).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance: TrustedContact) -> None:
        services.remove_contact(instance)

    @extend_schema(request=None, responses=TrustedContactSerializer)
    @action(detail=True, methods=["post"], url_path="resend-invitation")
    def resend_invitation(self, request: Request, pk: str | None = None) -> Response:
        contact = self.get_object()
        services.resend_invitation(contact)
        return Response(TrustedContactSerializer(contact).data)


class ConsentViewSet(OwnedModelViewSet):
    """The student's consents. The list is also their consent history.

    POST turns something on, DELETE withdraws it. Withdrawing keeps the row (marked
    withdrawn) so the history stays complete.
    """

    model = ConsentRecord
    serializer_class = ConsentSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[ConsentRecord]:
        return super().get_queryset().order_by("-granted_at")

    @extend_schema(request=ConsentCreateSerializer, responses={201: ConsentSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ConsentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = cast(User, request.user)
        if data["purpose"] == ConsentPurpose.PRIVACY_NOTICE:
            consent = services.record_privacy_notice(user, data["notice_version"])
        else:
            if "contact" not in data or "preview_hash" not in data:
                raise services.fail(
                    "Choose a contact and preview the message before turning this on.",
                    "preview_required",
                )
            consent = services.grant_weekly_consent(
                user,
                _own_contact(user, data["contact"]),
                notice_version=data["notice_version"],
                preview_hash=data["preview_hash"],
                send_weekday=data.get("send_weekday", DEFAULT_WEEKDAY),
                send_hour=data.get("send_hour", DEFAULT_HOUR),
            )
        return Response(ConsentSerializer(consent).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: ConsentSerializer})
    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        consent = self.get_object()
        services.revoke_consent(consent)
        return Response(ConsentSerializer(consent).data)

    def _change(self, change: Any) -> Response:
        consent = self.get_object()
        change(consent)
        return Response(ConsentSerializer(consent).data)

    @extend_schema(request=None, responses=ConsentSerializer)
    @action(detail=True, methods=["post"])
    def pause(self, request: Request, pk: str | None = None) -> Response:
        return self._change(services.pause_consent)

    @extend_schema(request=None, responses=ConsentSerializer)
    @action(detail=True, methods=["post"])
    def resume(self, request: Request, pk: str | None = None) -> Response:
        return self._change(services.resume_consent)

    @extend_schema(request=None, responses=ConsentSerializer)
    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk: str | None = None) -> Response:
        return self._change(services.reconfirm_consent)


class WeeklyPreviewView(APIView):
    """GET /api/v1/sharing/preview?contact=<id>: the exact note, before anything is on."""

    @extend_schema(
        parameters=[OpenApiParameter("contact", str, required=True)],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)
        contact = _own_contact(user, request.query_params.get("contact") or None)
        week_start, week_end = covered_week(timezone.now(), user_zone(user))
        fields = collect_weekly_fields(user, week_start, week_end)
        message = render_weekly(fields)
        return Response(
            {
                "recipient": {"id": str(contact.pk), "name": contact.name, "email": contact.email},
                "recipient_can_receive": contact.status == ContactStatus.CONFIRMED,
                "subject": message.subject,
                "body": f"{message.body}\n\n{UNSUBSCRIBE_PREVIEW_LINE}",
                "fields_shared": list(ALLOWED_FIELDS),
                "values": {
                    "display_name": fields.display_name,
                    "week_start": fields.week_start.isoformat(),
                    "week_end": fields.week_end.isoformat(),
                    "check_in_days": fields.check_in_days,
                },
                "notice": WEEKLY_NOTICE,
                "notice_version": WEEKLY_NOTICE_VERSION,
                "preview_hash": weekly_format_hash(),
                "default_schedule": {"send_weekday": DEFAULT_WEEKDAY, "send_hour": DEFAULT_HOUR},
                "reconfirm_every_days": settings.CONSENT_RECONFIRM_DAYS,
            }
        )


class NoticeVersionsView(APIView):
    """GET /api/v1/sharing/notices: the versions a consent request must quote."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, auth=[])
    def get(self, request: Request) -> Response:
        return Response(
            {
                "privacy_notice_version": PRIVACY_NOTICE_VERSION,
                "weekly_notice_version": WEEKLY_NOTICE_VERSION,
                "weekly_notice": WEEKLY_NOTICE,
            }
        )


# --- Support (SOS) ---------------------------------------------------------------


class SosPreviewView(APIView):
    """POST /api/v1/sos/preview: the exact recipient and message. Sends nothing."""

    @extend_schema(request=SosPreviewSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request: Request) -> Response:
        serializer = SosPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = cast(User, request.user)
        contact = _own_contact(user, serializer.validated_data["contact"])
        message = sos.build_sos_message(user, contact)
        return Response(
            {
                "recipient": {"id": str(contact.pk), "name": contact.name, "email": contact.email},
                "recipient_can_receive": contact.status == ContactStatus.CONFIRMED,
                "subject": message.subject,
                "body": sos.preview_text(message),
                "message_hash": message.message_hash,
                "limits": (
                    "This app is not monitored. It cannot tell you whether the message "
                    "was read, and it cannot guarantee a reply."
                ),
            }
        )


class SosNotifyContactView(APIView):
    """POST /api/v1/sos/notify-contact: send the message the student just approved.

    Requires the contact id, the hash of the text that was shown, a one-time key and
    `confirmed: true`. Nothing else in the system can send this message.
    """

    throttle_classes = [SosThrottle]

    @extend_schema(request=SosSendSerializer, responses={202: OpenApiTypes.OBJECT})
    def post(self, request: Request) -> Response:
        serializer = SosSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = cast(User, request.user)
        notification, _ = sos.request_sos(
            user,
            _own_contact(user, data["contact"]),
            message_hash=data["message_hash"],
            idempotency_key=str(data["idempotency_key"]),
        )
        return Response(
            {
                "notification_id": str(notification.pk),
                "status": notification.status,
                # Deliberately not "sent" or "delivered": only what is known to be true.
                "detail": (
                    "Your message is queued to send. This app cannot tell you whether "
                    "it has been read. If you need support now, you can call a helpline."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


# --- Links opened by the contact (no account) ------------------------------------


class _ContactLinkView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicTokenThrottle]
    purpose = INVITE

    def _contact(self, request: Request, serializer_class: Any = ContactTokenSerializer) -> Any:
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = contact_from_token(serializer.validated_data["token"], self.purpose)
        return contact, serializer.validated_data


class InvitationView(_ContactLinkView):
    """POST /api/v1/contact-invitations/view: who is asking, and what it means."""

    @extend_schema(request=ContactTokenSerializer, responses={200: OpenApiTypes.OBJECT}, auth=[])
    def post(self, request: Request) -> Response:
        contact, _ = self._contact(request)
        if contact is None:
            return Response(BAD_LINK, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "from_name": services.display_name_of(contact.user),
                "status": contact.status,
                "what_you_may_receive": [
                    "A short weekly note with how many days they checked in. No details.",
                    "A message they choose to send when they would like to hear from you.",
                ],
                "limits": (
                    "This app is not monitored and is not an emergency service. You will "
                    "not get an account or see any of their records."
                ),
            }
        )


class InvitationAcceptView(_ContactLinkView):
    @extend_schema(request=ContactTokenSerializer, responses={200: OpenApiTypes.OBJECT}, auth=[])
    def post(self, request: Request) -> Response:
        contact, _ = self._contact(request)
        if contact is None:
            return Response(BAD_LINK, status=status.HTTP_400_BAD_REQUEST)
        services.accept_invitation(contact)
        return Response(
            {"detail": "You have agreed to receive messages. You can unsubscribe at any time."}
        )


class InvitationDeclineView(_ContactLinkView):
    @extend_schema(request=ContactTokenSerializer, responses={200: OpenApiTypes.OBJECT}, auth=[])
    def post(self, request: Request) -> Response:
        contact, _ = self._contact(request)
        if contact is None:
            return Response(BAD_LINK, status=status.HTTP_400_BAD_REQUEST)
        services.decline_invitation(contact)
        return Response({"detail": "You have declined. You will not receive any messages."})


class UnsubscribeView(_ContactLinkView):
    """POST /api/v1/unsubscribe: stop messages, from the link in any email."""

    purpose = UNSUBSCRIBE

    @extend_schema(request=UnsubscribeSerializer, responses={200: OpenApiTypes.OBJECT}, auth=[])
    def post(self, request: Request) -> Response:
        contact, data = self._contact(request, UnsubscribeSerializer)
        if contact is None:
            return Response(BAD_LINK, status=status.HTTP_400_BAD_REQUEST)
        services.unsubscribe(contact, block_all=data["block_all"])
        return Response({"detail": "You are unsubscribed. No more messages will be sent to you."})


class OneClickUnsubscribeView(APIView):
    """POST /api/v1/unsubscribe/one-click?token=...

    The target of the List-Unsubscribe header (RFC 8058). Mail providers call it
    directly when someone presses "unsubscribe" in their mail app, so it takes no
    cookies and no CSRF token: the signed token is the only credential.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [PublicTokenThrottle]

    @extend_schema(
        parameters=[OpenApiParameter("token", str, required=True)],
        request=None,
        responses={200: OpenApiTypes.OBJECT},
        auth=[],
    )
    def post(self, request: Request) -> Response:
        contact = contact_from_token(request.query_params.get("token", ""), UNSUBSCRIBE)
        if contact is None:
            return Response(BAD_LINK, status=status.HTTP_400_BAD_REQUEST)
        services.unsubscribe(contact)
        return Response({"detail": "You are unsubscribed."})
