"""Configuration for Meshup presence app."""
from django.apps import AppConfig


class PresenceConfig(AppConfig):
    """Application configuration for presence tracking."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.presence"
    verbose_name = "Meshup Presence"
