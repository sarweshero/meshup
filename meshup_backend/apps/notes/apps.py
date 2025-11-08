"""Configuration for Meshup notes app."""
from django.apps import AppConfig


class NotesConfig(AppConfig):
    """Application configuration for collaborative notes."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notes"
    verbose_name = "Meshup Notes"
