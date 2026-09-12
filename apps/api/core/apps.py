from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Núcleo"

    def ready(self) -> None:
        # Registra el ajuste de PRAGMAs de SQLite en cada conexión nueva.
        from core import db  # noqa: F401
