from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import DetalleMovimiento
from .stock import verificar_stock_no_negativo


@receiver(post_delete, sender=DetalleMovimiento)
def validar_stock_tras_borrar(sender, instance, **kwargs):
    # Se ejecuta dentro de la transacción del borrado: si el stock quedara
    # negativo (p. ej. al borrar una entrada ya consumida) se revierte todo.
    # También cubre borrados en cascada y borrados masivos (queryset.delete()).
    verificar_stock_no_negativo([instance.fk_lot_id])
