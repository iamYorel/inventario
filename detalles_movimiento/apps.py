from django.apps import AppConfig


class DetallesMovimientoConfig(AppConfig):
    name = 'detalles_movimiento'

    def ready(self):
        from . import signals  # noqa: F401
