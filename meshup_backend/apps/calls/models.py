"""Models for voice and video call management.
Tracks call sessions, participants, and call history."""

from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class CallSession(models.Model):
    """Call session model tracking voice/video calls."""

    CALL_TYPES = (
        ("voice", "Voice Call"),
        ("video", "Video Call"),
        ("group", "Group Call"),
    )

    STATUS_CHOICES = (
        ("initiating", "Initiating"),
        ("ringing", "Ringing"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("ended", "Ended"),
        ("missed", "Missed"),
        ("declined", "Declined"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_type = models.CharField(max_length=20, choices=CALL_TYPES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiating", db_index=True)
    initiator = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="initiated_calls",
    )
    channel = models.ForeignKey(
        "meshup_channels.Channel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voice_calls",
    )
    dm_channel = models.ForeignKey(
        "meshup_messages.DirectMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voice_calls",
    )
    server = models.ForeignKey(
        "servers.Server",
        on_delete=models.CASCADE,
        related_name="call_sessions",
    )
    call_token = models.CharField(max_length=500, unique=True)
    room_id = models.CharField(max_length=255, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(null=True, blank=True)
    recording_size = models.BigIntegerField(null=True, blank=True)
    video_quality = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low (240p)"),
            ("standard", "Standard (480p)"),
            ("high", "High (720p)"),
            ("ultra", "Ultra (1080p)"),
        ],
        default="standard",
    )
    audio_codec = models.CharField(max_length=50, default="opus")
    video_codec = models.CharField(max_length=50, default="vp9")
    total_participants = models.IntegerField(default=2)
    peak_participants = models.IntegerField(default=2)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "call_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["initiator", "-created_at"]),
            models.Index(fields=["room_id"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["server", "-created_at"]),
        ]

    def __str__(self) -> str:
        duration = self.get_duration()
        return f"{self.call_type.upper()} - {self.initiator.username} - {duration}s"

    def get_duration(self) -> int:
        """Calculate call duration in seconds."""
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        if self.started_at:
            return int((timezone.now() - self.started_at).total_seconds())
        return 0

    def get_active_participants_count(self) -> int:
        """Return the number of currently active participants."""
        return self.participants.filter(left_at__isnull=True).count()


class CallParticipant(models.Model):
    """Participant model tracking individual call participation."""

    MEDIA_STATE_CHOICES = (
        ("active", "Active"),
        ("muted", "Muted"),
        ("off", "Off"),
    )

    SCREEN_SHARE_STATE_CHOICES = (
        ("inactive", "Inactive"),
        ("active", "Active"),
        ("paused", "Paused"),
    )

    NETWORK_QUALITY_CHOICES = (
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("poor", "Poor"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="call_participations")
    audio_state = models.CharField(max_length=20, choices=MEDIA_STATE_CHOICES, default="active")
    video_state = models.CharField(max_length=20, choices=MEDIA_STATE_CHOICES, default="active")
    screen_share_state = models.CharField(max_length=20, choices=SCREEN_SHARE_STATE_CHOICES, default="inactive")
    peer_id = models.CharField(max_length=255, unique=True, db_index=True)
    network_quality = models.CharField(max_length=20, choices=NETWORK_QUALITY_CHOICES, default="good")
    packet_loss_rate = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    latency_ms = models.IntegerField(default=0)
    bandwidth_mbps = models.FloatField(default=0.0)
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "call_participants"
        unique_together = [["call", "user"]]
        indexes = [
            models.Index(fields=["call", "joined_at"]),
            models.Index(fields=["peer_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} in {self.call.id}"

    def get_duration(self) -> int:
        """Return the participant call duration in seconds."""
        if self.left_at:
            return int((self.left_at - self.joined_at).total_seconds())
        return int((timezone.now() - self.joined_at).total_seconds())


class CallQualityMetric(models.Model):
    """Real-time quality metrics for call participants."""

    CONNECTION_STATE_CHOICES = (
        ("new", "New"),
        ("connecting", "Connecting"),
        ("connected", "Connected"),
        ("disconnected", "Disconnected"),
        ("failed", "Failed"),
        ("closed", "Closed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="quality_metrics")
    participant = models.ForeignKey(CallParticipant, on_delete=models.CASCADE, related_name="quality_metrics")
    audio_level = models.IntegerField(validators=[MinValueValidator(-127), MaxValueValidator(0)])
    audio_jitter_ms = models.FloatField()
    audio_round_trip_time_ms = models.FloatField()
    video_bitrate_kbps = models.IntegerField()
    video_framerate = models.IntegerField()
    video_resolution = models.CharField(max_length=20)
    video_encoder_implementation = models.CharField(max_length=50)
    bytes_sent = models.BigIntegerField()
    bytes_received = models.BigIntegerField()
    packets_lost = models.IntegerField()
    connection_state = models.CharField(max_length=20, choices=CONNECTION_STATE_CHOICES)
    cpu_usage_percent = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "call_quality_metrics"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["call", "-recorded_at"]),
            models.Index(fields=["participant", "-recorded_at"]),
        ]


class CallRecording(models.Model):
    """Call recording metadata and management."""

    STATUS_CHOICES = (
        ("recording", "Recording"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.OneToOneField(CallSession, on_delete=models.CASCADE, related_name="recording")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="recording")
    file_url = models.URLField()
    file_size = models.BigIntegerField()
    duration_seconds = models.IntegerField()
    transcript = models.TextField(blank=True)
    transcript_language = models.CharField(max_length=10, default="en")
    has_transcript = models.BooleanField(default=False)
    storage_regions = models.JSONField(default=list)
    is_public = models.BooleanField(default=False)
    allowed_viewers = models.ManyToManyField("users.User", related_name="accessible_call_recordings", blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "call_recordings"
        ordering = ["-created_at"]


class ScreenShareSession(models.Model):
    """Screen sharing session management."""

    STATUS_CHOICES = (
        ("active", "Active"),
        ("paused", "Paused"),
        ("ended", "Ended"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="screen_shares")
    participant = models.ForeignKey(CallParticipant, on_delete=models.CASCADE, related_name="screen_shares")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    stream_id = models.CharField(max_length=255, unique=True, db_index=True)
    resolution = models.CharField(max_length=20)
    framerate = models.IntegerField()
    bitrate_kbps = models.IntegerField()
    include_audio = models.BooleanField(default=False)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "screen_share_sessions"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["call", "status"]),
            models.Index(fields=["participant"]),
        ]

    def __str__(self) -> str:
        return f"Screen share by {self.participant.user.username}"


class CallInvitation(models.Model):
    """Call invitation tracking for missed calls."""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("missed", "Missed"),
    )

    NOTIFICATION_CHOICES = (
        ("push", "Push Notification"),
        ("email", "Email"),
        ("inapp", "In-App"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="invitations")
    recipient = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="call_invitations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    response_time_seconds = models.IntegerField(null=True, blank=True)
    notification_sent = models.BooleanField(default=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "call_invitations"
        unique_together = [["call", "recipient"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "status"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]
