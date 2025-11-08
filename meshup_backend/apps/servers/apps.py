"""Configuration for Meshup servers app."""
from django.apps import AppConfig


class ServersConfig(AppConfig):
    """Application configuration for server management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.servers"
    verbose_name = "Meshup Servers"
