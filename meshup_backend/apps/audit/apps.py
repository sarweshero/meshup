"""Application configuration for audit logging."""
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit and Security"

    def ready(self) -> None:  # pragma: no cover - import for signal registration only
        from . import signals  # noqa: F401

        return super().ready()
