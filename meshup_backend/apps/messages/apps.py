"""Configuration for Meshup messages app."""
from django.apps import AppConfig


class MessagesConfig(AppConfig):
    """Application configuration for messaging services."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messages"
    label = "meshup_messages"
    verbose_name = "Meshup Messages"
