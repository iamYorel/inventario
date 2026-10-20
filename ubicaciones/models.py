from django.db import models


class Ubicacion(models.Model):
    # Entidad débil: un estante solo existe dentro de un almacén.
    pk_ubi_id = models.AutoField(primary_key=True)
    fk_alm = models.ForeignKey(
        'almacenes.Almacen', on_delete=models.CASCADE,
        db_column='fk_alm_id', related_name='ubicaciones',
        verbose_name='almacén',
    )
    ubi_estante = models.CharField(max_length=30)
    ubi_descripcion = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'tbl_ubicacion'
        verbose_name = 'ubicación'
        verbose_name_plural = 'ubicaciones'
        constraints = [
            models.UniqueConstraint(fields=['fk_alm', 'ubi_estante'],
                                    name='uq_ubicacion_almacen_estante'),
        ]

    def __str__(self):
        return f'{self.ubi_estante} - {self.fk_alm.alm_nombre}'
