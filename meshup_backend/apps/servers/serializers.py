"""Serializers for servers and workspaces."""
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer

from .models import Server


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
