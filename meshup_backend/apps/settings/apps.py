"""Configuration for Meshup settings app."""
from django.apps import AppConfig


class MeshupSettingsConfig(AppConfig):
    """Application configuration for user and server settings."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.settings"
    verbose_name = "Meshup Settings"
