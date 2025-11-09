"""Authentication related models including audit logging."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Comprehensive audit log for sensitive operations."""

    ACTION_TYPES = (
        ("login", "User Login"),
        ("logout", "User Logout"),
        ("password_change", "Password Changed"),
        ("password_reset", "Password Reset"),
        ("resource_create", "Resource Created"),
        ("resource_update", "Resource Updated"),
        ("resource_delete", "Resource Deleted"),
        ("permission_grant", "Permission Granted"),
        ("permission_revoke", "Permission Revoked"),
        ("server_settings", "Server Settings Modified"),
        ("role_modified", "Role Modified"),
        ("member_ban", "Member Banned"),
        ("member_kick", "Member Kicked"),
        ("failed_login", "Failed Login Attempt"),
    )

    SEVERITY_LEVELS = (
        ("info", "Informational"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50, choices=ACTION_TYPES, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default="info")

    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_name = models.CharField(max_length=255, blank=True)

    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    change_description = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(max_length=500)

    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    status_code = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - human readable repr
        user_label = self.user if self.user else "anonymous"
        return f"{self.action} - {user_label} - {self.created_at}"


class LoginAttempt(models.Model):
    """Track successful and failed login attempts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "login_attempts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "-created_at"]),
            models.Index(fields=["ip_address", "-created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - human readable repr
        status = "success" if self.success else "failure"
        return f"Login {status} for {self.email}"