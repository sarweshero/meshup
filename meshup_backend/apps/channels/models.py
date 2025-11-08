"""Channel models for Meshup."""
import uuid

from django.db import models
from django.utils import timezone


class Channel(models.Model):
    """Channel model for organizing conversations within a server."""

    CHANNEL_TYPES = (
        ("text", "Text Channel"),
        ("voice", "Voice Channel"),
        ("announcement", "Announcement Channel"),
        ("stage", "Stage Channel"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="channels")
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, default="text")

    position = models.IntegerField(default=0)
    is_private = models.BooleanField(default=False)
    is_nsfw = models.BooleanField(default=False)
    slowmode_delay = models.IntegerField(default=0)

    parent_category = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="child_channels"
    )

    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="created_channels"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "channels"
        ordering = ["position", "created_at"]
        unique_together = [["server", "name"]]
        indexes = [
            models.Index(fields=["server", "position"]),
            models.Index(fields=["server", "channel_type"]),
        ]

    def __str__(self) -> str:
        return f"#{self.name} ({self.server.name})"
