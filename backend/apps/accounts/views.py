from __future__ import annotations

from typing import cast

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.views import CsrfProtectedAPIView

from . import services
from .models import User
from .serializers import (
    CsrfSerializer,
    DetailSerializer,
    EmailSerializer,
    LoginSerializer,
    MeSerializer,
    PasswordConfirmSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    TokenSerializer,
    check_password_strength,
)
from .throttles import (
    AccountDeleteThrottle,
    EmailActionThrottle,
    LoginEmailThrottle,
    LoginIPThrottle,
    RegisterThrottle,
)
from .tokens import read_email_verification_token, user_from_password_reset_parts

# One wording for every "we may have sent an email" response, so the reply never
# reveals whether an address has an account.
CHECK_EMAIL = "If that address can be used, we have sent an email to it. Check your inbox."
BAD_LINK = "This link is not valid or has expired. Request a new one."


def _detail(message: str, code: str | None = None, http_status: int = 200) -> Response:
    body = {"detail": message}
    if code:
        body["code"] = code
    return Response(body, status=http_status)


@method_decorator(never_cache, name="dispatch")
class CsrfView(APIView):
    """Hands the browser a CSRF token to send back in the X-CSRFToken header."""

    permission_classes = [AllowAny]

    @extend_schema(responses=CsrfSerializer)
    def get(self, request: Request) -> Response:
        return Response({"csrf_token": get_token(request)})


class RegisterView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: DetailSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.register_user(
            email=data["email"],
            password=data["password"],
            preferred_language=data["preferred_language"],
            timezone_name=data["timezone"],
            display_name=data["display_name"],
        )
        return _detail(CHECK_EMAIL, http_status=status.HTTP_201_CREATED)


class VerifyEmailView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=TokenSerializer, responses={200: DetailSerializer, 400: DetailSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = read_email_verification_token(serializer.validated_data["token"])
        if user_id is None or not services.verify_email(user_id):
            return _detail(BAD_LINK, "invalid_link", status.HTTP_400_BAD_REQUEST)
        return _detail("Your email is confirmed. You can sign in now.")


class ResendVerificationView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [EmailActionThrottle]

    @extend_schema(request=EmailSerializer, responses=DetailSerializer)
    def post(self, request: Request) -> Response:
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_verification_email(serializer.validated_data["email"])
        return _detail(CHECK_EMAIL)


class LoginView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={200: MeSerializer, 400: DetailSerializer, 403: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return _detail(
                "Email or password is incorrect.",
                "invalid_credentials",
                status.HTTP_400_BAD_REQUEST,
            )
        if not user.email_verified:
            return _detail(
                "Confirm your email before signing in. We can send the link again.",
                "email_not_verified",
                status.HTTP_403_FORBIDDEN,
            )
        login(request, user)  # also rotates the session key
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(request.user).data)

    @extend_schema(request=MeSerializer, responses=MeSerializer)
    def patch(self, request: Request) -> Response:
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordResetRequestView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [EmailActionThrottle]

    @extend_schema(request=EmailSerializer, responses=DetailSerializer)
    def post(self, request: Request) -> Response:
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return _detail(CHECK_EMAIL)


class PasswordResetConfirmView(CsrfProtectedAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [EmailActionThrottle]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: DetailSerializer, 400: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = user_from_password_reset_parts(data["uid"], data["token"])
        if user is None:
            return _detail(BAD_LINK, "invalid_link", status.HTTP_400_BAD_REQUEST)
        try:
            check_password_strength(data["new_password"], user)
        except ValidationError as exc:
            raise ValidationError({"new_password": exc.detail}) from exc
        services.reset_password(user, data["new_password"])
        return _detail("Your password has been changed. Sign in with the new one.")


class AccountView(APIView):
    """DELETE /api/v1/account: ask for the account and everything in it to be erased."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AccountDeleteThrottle]

    @extend_schema(
        request=PasswordConfirmSerializer,
        responses={202: DetailSerializer, 400: DetailSerializer},
    )
    def delete(self, request: Request) -> Response:
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = cast(User, request.user)
        if not user.check_password(serializer.validated_data["password"]):
            return _detail(
                "That password is incorrect. Your account has not been deleted.",
                "invalid_password",
                status.HTTP_400_BAD_REQUEST,
            )
        services.request_account_deletion(user)
        logout(request)
        return _detail(
            "Your account is locked and is being deleted. You have been signed out.",
            http_status=status.HTTP_202_ACCEPTED,
        )
