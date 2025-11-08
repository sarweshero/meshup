"""Configuration for Meshup tasks app."""
from django.apps import AppConfig


class TasksConfig(AppConfig):
    """Application configuration for task management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
    verbose_name = "Meshup Tasks"
