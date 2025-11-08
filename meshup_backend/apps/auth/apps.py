"""Configuration for Meshup auth app."""
from django.apps import AppConfig


class MeshupAuthConfig(AppConfig):
    """Application configuration for authentication services."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth"
    label = "meshup_auth"
    verbose_name = "Meshup Authentication"
