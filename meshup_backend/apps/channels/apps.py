"""Configuration for Meshup channels app."""
from django.apps import AppConfig


class ChannelsConfig(AppConfig):
    """Application configuration for channel management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.channels"
    label = "meshup_channels"
    verbose_name = "Meshup Channels"
