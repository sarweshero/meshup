"""Models for user activity tracking and sharing."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class UserActivity(models.Model):
    """Track user activities in real-time."""

    ACTIVITY_STATES = (
        ("online", "Online"),
        ("away", "Away"),
        ("dnd", "Do Not Disturb"),
        ("invisible", "Invisible"),
        ("offline", "Offline"),
    )

    CURRENT_ACTIVITIES = (
        ("idle", "Idle"),
        ("browsing", "Browsing"),
        ("typing", "Typing"),
        ("in_call", "In Call"),
        ("in_meeting", "In Meeting"),
        ("streaming", "Streaming"),
        ("listening", "Listening to Audio"),
        ("watching", "Watching Video"),
        ("gaming", "Gaming"),
        ("custom", "Custom"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="activity")
    status = models.CharField(max_length=20, choices=ACTIVITY_STATES, default="offline", db_index=True)
    current_activity = models.CharField(max_length=20, choices=CURRENT_ACTIVITIES, default="idle")
    custom_activity_text = models.CharField(max_length=128, blank=True)
    custom_activity_emoji = models.CharField(max_length=10, blank=True)
    server = models.ForeignKey(
        "servers.Server",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_activities",
    )
    channel = models.ForeignKey(
        "meshup_channels.Channel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_activities",
    )
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)
    status_updated_at = models.DateTimeField(default=timezone.now)
    activity_started_at = models.DateTimeField(default=timezone.now)
    share_activity = models.BooleanField(default=True)
    activity_visibility = models.CharField(
        max_length=20,
        choices=[
            ("everyone", "Everyone"),
            ("friends", "Friends Only"),
            ("servers", "Servers Only"),
            ("hidden", "Hidden"),
        ],
        default="everyone",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_activities"
        indexes = [
            models.Index(fields=["status", "-last_seen"]),
            models.Index(fields=["server", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.status}"


class ActivityLog(models.Model):
    """Log of user activities for analytics and auditing."""

    ACTIVITY_TYPES = (
        ("message_sent", "Message Sent"),
        ("file_shared", "File Shared"),
        ("call_initiated", "Call Initiated"),
        ("call_joined", "Call Joined"),
        ("screen_shared", "Screen Shared"),
        ("task_created", "Task Created"),
        ("task_completed", "Task Completed"),
        ("note_created", "Note Created"),
        ("poll_created", "Poll Created"),
        ("poll_voted", "Poll Voted"),
        ("event_created", "Event Created"),
        ("event_rsvped", "Event RSVP"),
    )

    DEVICE_CHOICES = (
        ("desktop", "Desktop"),
        ("mobile", "Mobile"),
        ("tablet", "Tablet"),
        ("unknown", "Unknown"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="activity_logs")
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES, db_index=True)
    server = models.ForeignKey(
        "servers.Server",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    channel = models.ForeignKey(
        "meshup_channels.Channel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField()
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default="unknown")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
            models.Index(fields=["server", "-created_at"]),
        ]


class ActivityStreak(models.Model):
    """Track user activity streaks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="activity_streak")
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    streak_started_at = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "activity_streaks"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.current_streak} day streak"


class ShareableActivity(models.Model):
    """Rich activity objects that can be shared."""

    ACTIVITY_TYPES = (
        ("music", "Listening to Music"),
        ("game", "Playing Game"),
        ("article", "Reading Article"),
        ("video", "Watching Video"),
        ("podcast", "Listening to Podcast"),
        ("stream", "Watching Stream"),
        ("coding", "Coding"),
        ("designing", "Designing"),
        ("writing", "Writing"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="shareable_activity")
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(null=True, blank=True)
    service_name = models.CharField(max_length=100)
    service_id = models.CharField(max_length=255)
    external_url = models.URLField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    progress_seconds = models.IntegerField(default=0)
    is_public = models.BooleanField(default=True)
    started_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shareable_activities"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.activity_type}"


class OnlinePresence(models.Model):
    """Track online presence across servers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="online_presences")
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="online_presences")
    is_online = models.BooleanField(default=True, db_index=True)
    came_online_at = models.DateTimeField(default=timezone.now)
    went_offline_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "online_presences"
        unique_together = [["user", "server"]]
        indexes = [
            models.Index(fields=["server", "is_online"]),
            models.Index(fields=["user", "server"]),
        ]
