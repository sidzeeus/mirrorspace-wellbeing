from __future__ import annotations

from rest_framework import serializers

from .models import ConsentPurpose, ConsentRecord, TrustedContact

NAME_MAX_LENGTH = 80
RELATIONSHIP_MAX_LENGTH = 40


class TrustedContactSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    relationship = serializers.CharField(
        max_length=RELATIONSHIP_MAX_LENGTH, allow_blank=True, required=False, trim_whitespace=True
    )

    class Meta:
        model = TrustedContact
        fields = [
            "id",
            "name",
            "email",
            "relationship",
            "status",
            "invited_at",
            "responded_at",
            "created_at",
        ]
        read_only_fields = ["id", "status", "invited_at", "responded_at", "created_at"]


class TrustedContactUpdateSerializer(TrustedContactSerializer):
    """The address cannot be edited: a new address needs its own invitation."""

    # Declared fields ignore Meta.read_only_fields, so this has to be explicit.
    email = serializers.EmailField(read_only=True)


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = [
            "id",
            "purpose",
            "contact",
            "scope",
            "notice_version",
            "status",
            "status_reason",
            "granted_at",
            "last_confirmed_at",
            "paused_at",
            "revoked_at",
            "send_weekday",
            "send_hour",
            "next_send_at",
        ]
        read_only_fields = fields


class ConsentCreateSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=ConsentPurpose.values)
    notice_version = serializers.CharField(max_length=40)
    contact = serializers.UUIDField(required=False)
    preview_hash = serializers.CharField(max_length=64, required=False)
    # The student must send `true`. A missing or false value is refused.
    confirmed = serializers.BooleanField()
    send_weekday = serializers.IntegerField(min_value=0, max_value=6, required=False)
    send_hour = serializers.IntegerField(min_value=0, max_value=23, required=False)

    def validate_confirmed(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Confirm that you agree before this is turned on.")
        return value


class ContactTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)


class UnsubscribeSerializer(ContactTokenSerializer):
    block_all = serializers.BooleanField(default=False)


class SosPreviewSerializer(serializers.Serializer):
    contact = serializers.UUIDField()


class SosSendSerializer(serializers.Serializer):
    contact = serializers.UUIDField()
    message_hash = serializers.CharField(max_length=64)
    idempotency_key = serializers.UUIDField()
    confirmed = serializers.BooleanField()

    def validate_confirmed(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError(
                "Nothing was sent. Confirm the recipient and message to send it."
            )
        return value
