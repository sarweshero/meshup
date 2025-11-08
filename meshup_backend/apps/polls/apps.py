"""Configuration for Meshup polls app."""
from django.apps import AppConfig


class PollsConfig(AppConfig):
    """Application configuration for polls and surveys."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.polls"
    verbose_name = "Meshup Polls"
