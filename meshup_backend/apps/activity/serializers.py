"""Serializers for activity tracking and sharing."""

from __future__ import annotations

from rest_framework import serializers

from .models import ActivityLog, ActivityStreak, OnlinePresence, ShareableActivity, UserActivity
from apps.users.serializers import UserBasicSerializer


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activity."""

    user = UserBasicSerializer(read_only=True)
    time_since_active = serializers.SerializerMethodField()

    class Meta:
        model = UserActivity
        fields = (
            "id",
            "user",
            "status",
            "current_activity",
            "custom_activity_text",
            "custom_activity_emoji",
            "server",
            "channel",
            "last_seen",
            "activity_started_at",
            "share_activity",
            "time_since_active",
        )
        read_only_fields = ("id", "user", "last_seen")

    def get_time_since_active(self, obj: UserActivity) -> float:
        from django.utils import timezone

        delta = timezone.now() - obj.last_seen
        return delta.total_seconds()


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity logs."""

    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = (
            "id",
            "user",
            "activity_type",
            "server",
            "channel",
            "resource_type",
            "resource_id",
            "details",
            "device_type",
            "created_at",
        )
        read_only_fields = ("id", "user", "created_at")


class ActivityStreakSerializer(serializers.ModelSerializer):
    """Serializer for activity streaks."""

    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = ActivityStreak
        fields = (
            "id",
            "user",
            "current_streak",
            "best_streak",
            "last_active_date",
            "streak_started_at",
        )
        read_only_fields = ("id", "user")


class ShareableActivitySerializer(serializers.ModelSerializer):
    """Read serializer for shareable activities."""

    user = UserBasicSerializer(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = ShareableActivity
        fields = (
            "id",
            "user",
            "activity_type",
            "title",
            "description",
            "image_url",
            "service_name",
            "service_id",
            "external_url",
            "duration_seconds",
            "progress_seconds",
            "progress_percent",
            "is_public",
            "started_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "started_at", "updated_at")

    def get_progress_percent(self, obj: ShareableActivity) -> float:
        if obj.duration_seconds and obj.duration_seconds > 0:
            return round((obj.progress_seconds / obj.duration_seconds) * 100, 2)
        return 0.0


class ShareableActivityWriteSerializer(serializers.ModelSerializer):
    """Write serializer for shareable activities."""

    class Meta:
        model = ShareableActivity
        fields = (
            "id",
            "activity_type",
            "title",
            "description",
            "image_url",
            "service_name",
            "service_id",
            "external_url",
            "duration_seconds",
            "progress_seconds",
            "is_public",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().update(instance, validated_data)


class OnlinePresenceSerializer(serializers.ModelSerializer):
    """Serializer for online presence."""

    user = UserBasicSerializer(read_only=True)
    session_duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = OnlinePresence
        fields = (
            "id",
            "user",
            "server",
            "is_online",
            "came_online_at",
            "went_offline_at",
            "session_duration_seconds",
        )
        read_only_fields = ("id", "came_online_at", "went_offline_at")

    def get_session_duration_seconds(self, obj: OnlinePresence) -> float:
        from django.utils import timezone

        end = obj.went_offline_at or timezone.now()
        return (end - obj.came_online_at).total_seconds()


class UpdateActivitySerializer(serializers.Serializer):
    """Serializer for updating user activity."""

    status = serializers.ChoiceField(
        choices=["online", "away", "dnd", "invisible", "offline"],
        required=False,
    )
    current_activity = serializers.ChoiceField(
        choices=[
            "idle",
            "browsing",
            "typing",
            "in_call",
            "in_meeting",
            "streaming",
            "listening",
            "watching",
            "gaming",
            "custom",
        ],
        required=False,
    )
    custom_activity_text = serializers.CharField(max_length=128, required=False)
    custom_activity_emoji = serializers.CharField(max_length=10, required=False)
    channel_id = serializers.UUIDField(required=False, allow_null=True)


class ShareActivitySerializer(serializers.Serializer):
    """Serializer for sharing current activity."""

    ACTIVITY_TYPE_CHOICES = [
        ("music", "Listening to Music"),
        ("game", "Playing Game"),
        ("article", "Reading Article"),
        ("video", "Watching Video"),
        ("podcast", "Listening to Podcast"),
    ]

    activity_type = serializers.ChoiceField(choices=ACTIVITY_TYPE_CHOICES)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    image_url = serializers.URLField(required=False, allow_null=True)
    service_name = serializers.CharField(max_length=100)
    service_id = serializers.CharField(max_length=255)
    external_url = serializers.URLField(required=False, allow_null=True)
    duration_seconds = serializers.IntegerField(required=False, allow_null=True)
    is_public = serializers.BooleanField(default=True)
