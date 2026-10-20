from django.db import models


class Lote(models.Model):
    # Entidad débil: un lote solo existe para un artículo.
    pk_lot_id = models.AutoField(primary_key=True)
    fk_art = models.ForeignKey(
        'articulos.Articulo', on_delete=models.CASCADE,
        db_column='fk_art_id', related_name='lotes',
        verbose_name='artículo',
    )
    fk_ubi = models.ForeignKey(
        'ubicaciones.Ubicacion', on_delete=models.PROTECT,
        db_column='fk_ubi_id', related_name='lotes',
        verbose_name='ubicación',
    )
    lot_codigo = models.CharField(max_length=30)
    lot_fecha_vencimiento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_lote'
        constraints = [
            models.UniqueConstraint(fields=['fk_art', 'lot_codigo'],
                                    name='uq_lote_articulo_codigo'),
        ]

    def __str__(self):
        return f'Lote {self.lot_codigo} ({self.fk_art.art_nombre})'

    @property
    def stock(self):
        from detalles_movimiento.stock import calcular_stock
        return calcular_stock(fk_lot=self)
