"""Serializers for channel management."""
from rest_framework import serializers

from .models import Channel


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for channel details."""

    class Meta:
        model = Channel
        fields = (
            "id",
            "server",
            "name",
            "description",
            "channel_type",
            "position",
            "is_private",
            "is_nsfw",
            "slowmode_delay",
            "parent_category",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "server", "created_by", "created_at", "updated_at")
