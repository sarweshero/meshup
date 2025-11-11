"""Serializers for realtime API metadata."""
from __future__ import annotations

from rest_framework import serializers


class EventDescriptorSerializer(serializers.Serializer):
    """Describe a realtime websocket event."""

    key = serializers.CharField(help_text="Event identifier as sent in the websocket payload.")
    description = serializers.CharField()


class RealtimeMetadataResponseSerializer(serializers.Serializer):
    """Schema for realtime capability metadata."""

    websocket_url = serializers.CharField(help_text="Base websocket endpoint for channel subscriptions.")
    authentication = serializers.CharField(help_text="Authentication scheme used to authorize websocket connections.")
    events = EventDescriptorSerializer(many=True)
    direct_message_websocket_url = serializers.CharField(
        help_text="Base websocket endpoint for direct message subscriptions.",
        required=False,
    )
    direct_message_events = EventDescriptorSerializer(many=True, required=False)
