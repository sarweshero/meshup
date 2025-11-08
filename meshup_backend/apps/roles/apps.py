"""Configuration for Meshup roles app."""
from django.apps import AppConfig


class RolesConfig(AppConfig):
    """Application configuration for roles and permissions."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.roles"
    verbose_name = "Meshup Roles"
