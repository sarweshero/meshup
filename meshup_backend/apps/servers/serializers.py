"""Serializers for servers and workspaces."""
from django.utils import timezone
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer

from .models import Server, ServerInvite


class ServerSerializer(serializers.ModelSerializer):
    """Serializer for server details."""

    owner = UserBasicSerializer(read_only=True)

    class Meta:
        model = Server
        fields = (
            "id",
            "name",
            "description",
            "icon",
            "banner",
            "region",
            "is_public",
            "verification_level",
            "owner",
            "created_at",
            "updated_at",
            "member_count",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at", "member_count")


class ServerCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating or updating servers."""

    class Meta:
        model = Server
        fields = ("name", "description", "region", "is_public", "verification_level", "icon", "banner")


class ServerInviteSerializer(serializers.ModelSerializer):
    """Expose invite metadata to clients."""

    server = ServerSerializer(read_only=True)
    inviter = UserBasicSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = ServerInvite
        fields = (
            "id",
            "code",
            "server",
            "inviter",
            "label",
            "invitee_email",
            "max_uses",
            "uses",
            "expires_at",
            "revoked_at",
            "created_at",
            "is_active",
        )
        read_only_fields = (
            "id",
            "code",
            "uses",
            "revoked_at",
            "created_at",
            "is_active",
            "server",
            "inviter",
        )

    def get_is_active(self, obj: ServerInvite) -> bool:
        return obj.is_active()


class ServerInviteCreateSerializer(serializers.ModelSerializer):
    """Validate invite creation payload."""

    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = ServerInvite
        fields = ("label", "invitee_email", "max_uses", "expires_at")

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration must be in the future.")
        return value

    def validate_max_uses(self, value):
        if value is not None and value == 0:
            raise serializers.ValidationError("max_uses must be greater than zero or omitted.")
        return value


class ServerInviteAcceptSerializer(serializers.Serializer):
    """Payload for accepting an invite code."""

    code = serializers.CharField(max_length=32)
