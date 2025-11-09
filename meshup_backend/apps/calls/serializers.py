"""Serializers for voice and video call management."""

from __future__ import annotations

from rest_framework import serializers

from .models import (
    CallInvitation,
    CallParticipant,
    CallQualityMetric,
    CallRecording,
    CallSession,
    ScreenShareSession,
)
from apps.users.serializers import UserBasicSerializer


class CallParticipantSerializer(serializers.ModelSerializer):
    """Serializer for call participants."""

    user = UserBasicSerializer(read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = CallParticipant
        fields = (
            "id",
            "user",
            "audio_state",
            "video_state",
            "screen_share_state",
            "peer_id",
            "network_quality",
            "packet_loss_rate",
            "latency_ms",
            "bandwidth_mbps",
            "joined_at",
            "left_at",
            "duration_seconds",
        )
        read_only_fields = ("id", "peer_id", "joined_at", "left_at")

    def get_duration_seconds(self, obj: CallParticipant) -> int:
        """Calculate participant duration."""
        return obj.get_duration()


class CallQualityMetricSerializer(serializers.ModelSerializer):
    """Serializer for call quality metrics."""

    class Meta:
        model = CallQualityMetric
        fields = (
            "id",
            "audio_level",
            "audio_jitter_ms",
            "audio_round_trip_time_ms",
            "video_bitrate_kbps",
            "video_framerate",
            "video_resolution",
            "bytes_sent",
            "bytes_received",
            "packets_lost",
            "connection_state",
            "cpu_usage_percent",
            "recorded_at",
        )
        read_only_fields = ("id", "recorded_at")


class CallRecordingSerializer(serializers.ModelSerializer):
    """Serializer for call recordings."""

    duration_minutes = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = CallRecording
        fields = (
            "id",
            "call",
            "status",
            "file_url",
            "file_size",
            "file_size_mb",
            "duration_seconds",
            "duration_minutes",
            "transcript",
            "has_transcript",
            "is_public",
            "started_at",
            "completed_at",
        )
        read_only_fields = ("id", "call", "status", "file_url", "file_size", "transcript")

    def get_duration_minutes(self, obj: CallRecording) -> int:
        return obj.duration_seconds // 60 if obj.duration_seconds else 0

    def get_file_size_mb(self, obj: CallRecording) -> float:
        return round(obj.file_size / (1024 * 1024), 2) if obj.file_size else 0.0


class ScreenShareSessionSerializer(serializers.ModelSerializer):
    """Serializer for screen share sessions."""

    participant = CallParticipantSerializer(read_only=True)

    class Meta:
        model = ScreenShareSession
        fields = (
            "id",
            "call",
            "participant",
            "status",
            "stream_id",
            "resolution",
            "framerate",
            "bitrate_kbps",
            "include_audio",
            "started_at",
            "ended_at",
        )
        read_only_fields = ("id", "stream_id", "started_at", "ended_at")


class CallSessionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for call list."""

    initiator = UserBasicSerializer(read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = CallSession
        fields = (
            "id",
            "call_type",
            "status",
            "initiator",
            "room_id",
            "started_at",
            "ended_at",
            "duration_seconds",
            "participant_count",
            "is_recorded",
            "created_at",
        )
        read_only_fields = ("id", "initiator", "created_at")

    def get_duration_seconds(self, obj: CallSession) -> int:
        return obj.get_duration()

    def get_participant_count(self, obj: CallSession) -> int:
        return obj.participants.count()


class CallSessionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual call."""

    initiator = UserBasicSerializer(read_only=True)
    participants = CallParticipantSerializer(many=True, read_only=True)
    screen_shares = ScreenShareSessionSerializer(many=True, read_only=True)
    recording = CallRecordingSerializer(read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    quality_metrics = CallQualityMetricSerializer(many=True, read_only=True)

    class Meta:
        model = CallSession
        fields = (
            "id",
            "call_type",
            "status",
            "initiator",
            "channel",
            "dm_channel",
            "room_id",
            "call_token",
            "started_at",
            "ended_at",
            "duration_seconds",
            "video_quality",
            "audio_codec",
            "video_codec",
            "participants",
            "screen_shares",
            "recording",
            "total_participants",
            "peak_participants",
            "quality_metrics",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "call_token", "room_id", "initiator", "created_at", "updated_at")

    def get_duration_seconds(self, obj: CallSession) -> int:
        return obj.get_duration()


class CallInvitationSerializer(serializers.ModelSerializer):
    """Serializer for call invitations."""

    call = CallSessionListSerializer(read_only=True)
    initiator_info = serializers.SerializerMethodField()

    class Meta:
        model = CallInvitation
        fields = (
            "id",
            "call",
            "initiator_info",
            "status",
            "created_at",
            "responded_at",
            "response_time_seconds",
            "notification_type",
        )
        read_only_fields = ("id", "call", "created_at", "responded_at")

    def get_initiator_info(self, obj: CallInvitation) -> dict[str, object]:
        return UserBasicSerializer(obj.call.initiator).data


class InitiateCallSerializer(serializers.Serializer):
    """Serializer for initiating a call."""

    call_type = serializers.ChoiceField(choices=["voice", "video"])
    recipients = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of user IDs to invite to call",
    )
    channel_id = serializers.UUIDField(required=False, allow_null=True)
    dm_channel_id = serializers.UUIDField(required=False, allow_null=True)
    video_quality = serializers.ChoiceField(choices=["low", "standard", "high", "ultra"], default="standard")
    enable_recording = serializers.BooleanField(default=False)

    def validate(self, data: dict[str, object]) -> dict[str, object]:
        """Ensure either channel or DM channel is provided."""
        if not data.get("channel_id") and not data.get("dm_channel_id"):
            raise serializers.ValidationError("Either channel_id or dm_channel_id is required")
        if data.get("channel_id") and data.get("dm_channel_id"):
            raise serializers.ValidationError("Provide only one of channel_id or dm_channel_id")
        return data


class UpdateCallStatusSerializer(serializers.Serializer):
    """Serializer for updating call status."""

    status = serializers.ChoiceField(choices=["active", "on_hold", "ended"])


class UpdateMediaStateSerializer(serializers.Serializer):
    """Serializer for updating participant media state."""

    MEDIA_STATES = [
        ("active", "Active"),
        ("muted", "Muted"),
        ("off", "Off"),
    ]

    audio_state = serializers.ChoiceField(choices=MEDIA_STATES, required=False)
    video_state = serializers.ChoiceField(choices=MEDIA_STATES, required=False)
    screen_share_state = serializers.ChoiceField(
        choices=[
            ("inactive", "Inactive"),
            ("active", "Active"),
            ("paused", "Paused"),
        ],
        required=False,
    )


class ScreenShareStartSerializer(serializers.Serializer):
    """Serializer for starting screen share."""

    resolution = serializers.CharField(max_length=20, default="1920x1080")
    framerate = serializers.IntegerField(default=30)
    bitrate_kbps = serializers.IntegerField(default=2500)
    include_audio = serializers.BooleanField(default=False)
