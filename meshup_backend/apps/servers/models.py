"""Server and channel models for Meshup."""
import uuid

from django.db import models
from django.utils import timezone


class Server(models.Model):
    """Server (workspace) model for team collaboration."""

    REGION_CHOICES = (
        ("us-east", "US East"),
        ("us-west", "US West"),
        ("eu-central", "EU Central"),
        ("asia-pacific", "Asia Pacific"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="server_icons/", null=True, blank=True)
    banner = models.ImageField(upload_to="server_banners/", null=True, blank=True)

    region = models.CharField(max_length=20, choices=REGION_CHOICES, default="us-east")
    is_public = models.BooleanField(default=False)
    verification_level = models.IntegerField(default=0)

    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="owned_servers")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    member_count = models.IntegerField(default=0)

    class Meta:
        db_table = "servers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self) -> str:
        return self.name
