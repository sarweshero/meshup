"""Server and channel models for Meshup."""
import secrets
import string
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Server(models.Model):
    """Server (workspace) model for team collaboration."""

    REGION_CHOICES = tuple(getattr(settings, "SERVER_REGION_CHOICES", []))
    DEFAULT_REGION = REGION_CHOICES[0][0] if REGION_CHOICES else "global"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="server_icons/", null=True, blank=True)
    banner = models.ImageField(upload_to="server_banners/", null=True, blank=True)

    region = models.CharField(
        max_length=50,
        choices=REGION_CHOICES,
        default=DEFAULT_REGION,
    )
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


class ServerInvite(models.Model):
    """Invitation token granting access to a server."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name="invites")
    inviter = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invites",
    )
    code = models.CharField(max_length=16, unique=True, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    invitee_email = models.EmailField(blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Leave empty for unlimited")
    uses = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "server_invites"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["server", "created_at"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self) -> str:
        return f"Invite {self.code} -> {self.server.name}"

    @classmethod
    def generate_code(cls, length: int = 10) -> str:
        """Generate a unique invite code."""

        alphabet = string.ascii_uppercase + string.digits
        for _ in range(8):
            candidate = "".join(secrets.choice(alphabet) for _ in range(length))
            if not cls.objects.filter(code=candidate).exists():
                return candidate
        # Fallback to UUID hex to avoid collisions in extreme cases
        return uuid.uuid4().hex[: length].upper()

    def is_active(self) -> bool:
        """Return True if invite can still be redeemed."""

        if self.revoked_at is not None:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        return True

    def mark_used(self) -> None:
        """Increment usage counters when invite is redeemed."""

        self.uses += 1
        if self.max_uses is not None and self.uses >= self.max_uses and self.revoked_at is None:
            self.revoked_at = timezone.now()
