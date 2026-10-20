from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction


class DetalleMovimiento(models.Model):
    # Tabla intermedia del N:M Movimiento - Lote.
    pk_det_id = models.AutoField(primary_key=True)
    fk_mov = models.ForeignKey(
        'movimientos.Movimiento', on_delete=models.CASCADE,
        db_column='fk_mov_id', related_name='detalles',
        verbose_name='movimiento',
    )
    fk_lot = models.ForeignKey(
        'lotes.Lote', on_delete=models.PROTECT,
        db_column='fk_lot_id', related_name='detalles',
        verbose_name='lote',
    )
    det_cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(
            Decimal('0.01'), message='La cantidad debe ser mayor que cero.')],
    )

    class Meta:
        db_table = 'tbl_detalle_movimiento'
        verbose_name = 'detalle de movimiento'
        verbose_name_plural = 'detalles de movimiento'
        constraints = [
            # un lote aparece una sola vez por movimiento
            models.UniqueConstraint(fields=['fk_mov', 'fk_lot'],
                                    name='uq_detalle_movimiento_lote'),
            models.CheckConstraint(condition=models.Q(det_cantidad__gt=0),
                                   name='ck_detalle_cantidad_positiva'),
        ]

    def __str__(self):
        return f'{self.det_cantidad} de {self.fk_lot} en {self.fk_mov}'

    def save(self, *args, **kwargs):
        # Las reglas de stock viven en el modelo, no solo en el admin:
        # cualquier código que guarde un detalle pasa por aquí.
        from lotes.models import Lote
        from .stock import verificar_stock_no_negativo

        with transaction.atomic():
            lotes = {self.fk_lot_id}
            if self.pk:
                anterior = (DetalleMovimiento.objects.filter(pk=self.pk)
                            .values_list('fk_lot_id', flat=True).first())
                if anterior:
                    lotes.add(anterior)
            # Bloquea los lotes para que dos operaciones simultáneas no se
            # pisen (en SQLite no hace nada: allí ya se escribe de a una).
            list(Lote.objects.select_for_update()
                 .filter(pk__in=lotes).values_list('pk', flat=True))
            super().save(*args, **kwargs)
            verificar_stock_no_negativo(lotes)
