from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.realtime"
    verbose_name = "Realtime Services"

    def ready(self) -> None:  # pragma: no cover - import for side effects only
        from . import signals  # noqa: F401

        return super().ready()
