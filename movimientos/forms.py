from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet

from detalles_movimiento.stock import calcular_stock

from .models import Movimiento


class DetalleMovimientoFormSet(BaseInlineFormSet):
    """Valida, antes de guardar, que el movimiento no deje ningún lote con
    stock negativo (salida mayor a lo disponible, o entrada editada a la
    baja que ya fue consumida). La regla definitiva está en el modelo; esto
    solo permite mostrar un error claro en el formulario."""

    def clean(self):
        super().clean()
        tipo = self.instance.mov_tipo
        if tipo not in (Movimiento.ENTRADA, Movimiento.SALIDA):
            return
        signo = 1 if tipo == Movimiento.ENTRADA else -1

        lotes, cantidades = {}, {}
        for form in self.forms:
            datos = getattr(form, 'cleaned_data', None)
            if not datos or datos.get('DELETE'):
                continue
            lote, cantidad = datos.get('fk_lot'), datos.get('det_cantidad')
            if lote is None or cantidad is None:
                continue
            lotes[lote.pk] = lote
            cantidades[lote.pk] = cantidades.get(lote.pk, 0) + cantidad

        if self.instance.pk:  # al editar, también cuentan los lotes ya guardados
            for det in self.instance.detalles.select_related('fk_lot'):
                lotes.setdefault(det.fk_lot_id, det.fk_lot)

        for pk, lote in lotes.items():
            otros = calcular_stock(fk_lot=lote)
            if self.instance.pk:  # lo que ya aportaba este mismo movimiento
                otros -= calcular_stock(fk_lot=lote, fk_mov=self.instance)
            resultante = otros + signo * cantidades.get(pk, 0)
            if resultante < 0:
                raise ValidationError(
                    f'Stock insuficiente en {lote}: disponible {otros}, '
                    f'el movimiento dejaría el stock en {resultante}.')
