"""Role and permission models for Meshup RBAC."""
import uuid

from django.db import models
from django.utils import timezone


class Permission(models.Model):
    """Granular permissions for role-based access control."""

    PERMISSION_CATEGORIES = (
        ("server", "Server Management"),
        ("channel", "Channel Management"),
        ("message", "Message Management"),
        ("task", "Task Management"),
        ("note", "Note Management"),
        ("event", "Event Management"),
        ("poll", "Poll Management"),
        ("member", "Member Management"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=PERMISSION_CATEGORIES)
    is_dangerous = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "permissions"
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"


class Role(models.Model):
    """Custom roles with permission sets."""

    ROLE_TYPES = (
        ("admin", "Administrator"),
        ("manager", "Manager"),
        ("member", "Member"),
        ("guest", "Guest"),
        ("custom", "Custom Role"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    role_type = models.CharField(max_length=20, choices=ROLE_TYPES, default="custom")
    color = models.CharField(max_length=7, default="#99AAB5")
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    is_mentionable = models.BooleanField(default=True)
    is_hoisted = models.BooleanField(default=False)
    position = models.IntegerField(default=0)

    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="roles")
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="created_roles"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        ordering = ["-position", "name"]
        unique_together = [["server", "name"]]
        indexes = [
            models.Index(fields=["server", "position"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.server.name})"

    def has_permission(self, permission_codename: str) -> bool:
        """Check if role has specific permission."""
        return self.permissions.filter(codename=permission_codename).exists()


class ServerMember(models.Model):
    """Association between users and servers with role assignments."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="server_memberships")
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="members")
    roles = models.ManyToManyField(Role, related_name="members", blank=True)
    nickname = models.CharField(max_length=50, blank=True)

    is_owner = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_deafened = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)

    joined_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "server_members"
        unique_together = [["user", "server"]]
        ordering = ["-joined_at"]
        indexes = [
            models.Index(fields=["user", "server"]),
            models.Index(fields=["server", "is_banned"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} in {self.server.name}"

    def has_permission(self, permission_codename: str) -> bool:
        """Check if member has specific permission through any assigned role."""
        if self.is_owner:
            return True
        return self.roles.filter(permissions__codename=permission_codename).exists()
