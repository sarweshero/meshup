"""Configuration for Meshup events app."""
from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Application configuration for events and calendar."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
    verbose_name = "Meshup Events"
