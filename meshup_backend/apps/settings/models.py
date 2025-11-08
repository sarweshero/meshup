"""Settings models for Meshup."""
import uuid

from django.db import models


class UserSettings(models.Model):
    """User-level settings and preferences."""

    THEME_CHOICES = (("light", "Light"), ("dark", "Dark"), ("auto", "Auto"))
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
        ("ja", "Japanese"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="settings")
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="dark")
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    compact_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    desktop_notifications = models.BooleanField(default=True)
    notification_sound = models.BooleanField(default=True)
    notify_messages = models.BooleanField(default=True)
    notify_mentions = models.BooleanField(default=True)
    notify_tasks = models.BooleanField(default=True)
    notify_events = models.BooleanField(default=True)
    notify_polls = models.BooleanField(default=True)
    show_online_status = models.BooleanField(default=True)
    allow_direct_messages = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    reduced_motion = models.BooleanField(default=False)
    high_contrast = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_settings"

    def __str__(self) -> str:
        return f"Settings for {self.user.username}"


class ServerSettings(models.Model):
    """Server-level settings and configurations."""

    VERIFICATION_LEVELS = ((0, "None"), (1, "Low"), (2, "Medium"), (3, "High"), (4, "Highest"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.OneToOneField("servers.Server", on_delete=models.CASCADE, related_name="settings")
    default_notifications = models.BooleanField(default=True)
    explicit_content_filter = models.BooleanField(default=True)
    verification_level = models.IntegerField(choices=VERIFICATION_LEVELS, default=0)
    require_2fa_for_admin = models.BooleanField(default=False)
    auto_moderation = models.BooleanField(default=False)
    banned_words = models.JSONField(default=list, blank=True)
    enable_tasks = models.BooleanField(default=True)
    enable_notes = models.BooleanField(default=True)
    enable_events = models.BooleanField(default=True)
    enable_polls = models.BooleanField(default=True)
    max_members = models.IntegerField(default=100)
    max_channels = models.IntegerField(default=50)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "server_settings"

    def __str__(self) -> str:
        return f"Settings for {self.server.name}"


class NotificationPreference(models.Model):
    """Per-server notification preferences for users."""

    NOTIFICATION_LEVELS = (("all", "All Messages"), ("mentions", "Only Mentions"), ("nothing", "Nothing"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notification_preferences")
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="notification_preferences")
    notification_level = models.CharField(max_length=20, choices=NOTIFICATION_LEVELS, default="all")
    mute_server = models.BooleanField(default=False)
    mute_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_preferences"
        unique_together = [["user", "server"]]

    def __str__(self) -> str:
        return f"{self.user.username} notifications for {self.server.name}"
