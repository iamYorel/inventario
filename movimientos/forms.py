from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from detalles_movimiento.models import DetalleMovimiento
from detalles_movimiento.stock import calcular_stock, lotes_con_stock

from .models import Movimiento


class DetalleMovimientoFormSet(BaseInlineFormSet):
    """Valida, antes de guardar, que el movimiento no deje ningún lote con
    stock negativo (salida mayor a lo disponible, o entrada editada a la
    baja que ya fue consumida). La regla definitiva está en el modelo; esto
    solo permite mostrar un error claro en el formulario."""

    def get_unique_error_message(self, unique_check):
        return 'Un lote solo puede aparecer una vez en el movimiento.'

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
            if lote.pk in cantidades:
                raise ValidationError(
                    f'El lote {lote} está repetido en el movimiento: '
                    'agrega una sola línea por lote.')
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


# ---------------------------------------------------------------------------
# Formularios de la interfaz propia (no del panel de administración)
# ---------------------------------------------------------------------------

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ('mov_fecha', 'mov_tipo', 'mov_observacion')
        widgets = {
            'mov_fecha': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'),
            'mov_tipo': forms.Select(attrs={'class': 'form-select'}),
            'mov_observacion': forms.TextInput(
                attrs={'class': 'form-control',
                       'placeholder': 'Ej.: Compra inicial'}),
        }
        labels = {'mov_fecha': 'Fecha', 'mov_tipo': 'Tipo',
                  'mov_observacion': 'Observación'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # el tipo no se cambia una vez registrado (altera el stock)
            self.fields['mov_tipo'].disabled = True
            self.fields['mov_tipo'].help_text = (
                'No se puede cambiar: si hubo un error, registra un '
                'movimiento contrario.')


class LoteChoiceField(forms.ModelChoiceField):
    """Selector de lote que muestra artículo, ubicación y stock disponible."""

    def label_from_instance(self, lote):
        return (f'{lote.lot_codigo} · {lote.fk_art.art_nombre} · '
                f'{lote.fk_ubi} · stock {lote.stock_calc:g} '
                f'{lote.fk_art.art_unidad}')


class DetalleForm(forms.ModelForm):
    fk_lot = LoteChoiceField(
        label='Lote', empty_label='— Selecciona un lote —',
        queryset=lotes_con_stock().order_by('fk_art__art_nombre', 'lot_codigo'),
        widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = DetalleMovimiento
        fields = ('fk_lot', 'det_cantidad')
        widgets = {
            'det_cantidad': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }
        labels = {'det_cantidad': 'Cantidad'}


# Una línea mínima por movimiento; el formulario agrega más con JavaScript.
DetalleFormSet = inlineformset_factory(
    Movimiento, DetalleMovimiento, form=DetalleForm,
    formset=DetalleMovimientoFormSet,
    extra=0, min_num=1, validate_min=True, can_delete=True)
