from django.core.exceptions import ValidationError
from django.db import models


class Movimiento(models.Model):
    ENTRADA = 'entrada'
    SALIDA = 'salida'
    TIPOS = [
        (ENTRADA, 'Entrada'),
        (SALIDA, 'Salida'),
    ]

    pk_mov_id = models.AutoField(primary_key=True)
    mov_fecha = models.DateField()
    mov_tipo = models.CharField(max_length=10, choices=TIPOS)
    mov_observacion = models.CharField(max_length=200, blank=True)
    # N:M con Lote, resuelta con DetalleMovimiento
    lotes = models.ManyToManyField(
        'lotes.Lote', through='detalles_movimiento.DetalleMovimiento',
        related_name='movimientos',
    )

    class Meta:
        db_table = 'tbl_movimiento'
        verbose_name = 'movimiento'
        verbose_name_plural = 'movimientos'

    def __str__(self):
        return f'{self.get_mov_tipo_display()} #{self.pk_mov_id} ({self.mov_fecha})'

    def save(self, *args, **kwargs):
        # El tipo no se cambia después de registrado: convertir una entrada
        # en salida alteraría el stock de todos sus lotes. Si hubo un error,
        # se registra un movimiento contrario.
        if self.pk:
            anterior = (Movimiento.objects.filter(pk=self.pk)
                        .values_list('mov_tipo', flat=True).first())
            if anterior and anterior != self.mov_tipo:
                raise ValidationError(
                    'No se puede cambiar el tipo de un movimiento ya '
                    'registrado.')
        super().save(*args, **kwargs)
