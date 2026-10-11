from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User, validate_timezone

_LANGUAGE_CODES = [code for code, _ in settings.LANGUAGES]


def _check_timezone(value: str) -> str:
    try:
        validate_timezone(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc
    return value


def check_password_strength(password: str, user: User | None = None) -> str:
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc
    return password


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    age_confirmed = serializers.BooleanField()
    preferred_language = serializers.ChoiceField(
        choices=_LANGUAGE_CODES, default=settings.LANGUAGE_CODE
    )
    timezone = serializers.CharField(max_length=64, default=settings.DEFAULT_USER_TIMEZONE)
    display_name = serializers.CharField(max_length=60, allow_blank=True, default="")

    def validate_age_confirmed(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError(
                "You need to confirm that you are 18 or older to use this app."
            )
        return value

    def validate_timezone(self, value: str) -> str:
        return _check_timezone(value)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        candidate = User(email=attrs["email"])
        try:
            check_password_strength(attrs["password"], candidate)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc
        return attrs


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=128)
    token = serializers.CharField(max_length=256)
    new_password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class PasswordConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class MeSerializer(serializers.ModelSerializer):
    """The signed-in person's own account. Email cannot be changed here."""

    display_name = serializers.CharField(
        source="profile.display_name", max_length=60, allow_blank=True, required=False
    )
    timezone = serializers.CharField(source="profile.timezone", max_length=64, required=False)
    email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "email_verified",
            "preferred_language",
            "display_name",
            "timezone",
            "created_at",
        ]
        read_only_fields = ["id", "email", "email_verified", "created_at"]

    def validate_timezone(self, value: str) -> str:
        return _check_timezone(value)

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        profile_data = validated_data.pop("profile", {})
        if "preferred_language" in validated_data:
            instance.preferred_language = validated_data["preferred_language"]
            instance.save(update_fields=["preferred_language"])
        if profile_data:
            profile = instance.profile
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save(update_fields=[*profile_data.keys(), "updated_at"])
        return instance


class DetailSerializer(serializers.Serializer):
    """Shape of simple confirmation and error responses."""

    detail = serializers.CharField()
    code = serializers.CharField(required=False)


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()
