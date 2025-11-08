"""Configuration for Meshup users app."""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Application configuration for user management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Meshup Users"
