"""Serializers for Meshup settings."""
from rest_framework import serializers

from .models import NotificationPreference, ServerSettings, UserSettings


class UserSettingsSerializer(serializers.ModelSerializer):
    """Serializer for user settings."""

    class Meta:
        model = UserSettings
        fields = (
            "id",
            "theme",
            "language",
            "compact_mode",
            "email_notifications",
            "push_notifications",
            "desktop_notifications",
            "notification_sound",
            "notify_messages",
            "notify_mentions",
            "notify_tasks",
            "notify_events",
            "notify_polls",
            "show_online_status",
            "allow_direct_messages",
            "show_email",
            "reduced_motion",
            "high_contrast",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")


class ServerSettingsSerializer(serializers.ModelSerializer):
    """Serializer for server settings."""

    class Meta:
        model = ServerSettings
        fields = (
            "id",
            "default_notifications",
            "explicit_content_filter",
            "verification_level",
            "require_2fa_for_admin",
            "auto_moderation",
            "banned_words",
            "enable_tasks",
            "enable_notes",
            "enable_events",
            "enable_polls",
            "max_members",
            "max_channels",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""

    class Meta:
        model = NotificationPreference
        fields = ("id", "server", "notification_level", "mute_server", "mute_until", "updated_at")
        read_only_fields = ("id", "updated_at")
