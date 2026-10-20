from django.contrib import admin

from detalles_movimiento.models import DetalleMovimiento
from .forms import DetalleMovimientoFormSet
from .models import Movimiento


class DetalleMovimientoInline(admin.TabularInline):
    model = DetalleMovimiento
    formset = DetalleMovimientoFormSet
    extra = 1
    can_delete = False


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('pk_mov_id', 'mov_fecha', 'mov_tipo', 'mov_observacion')
    search_fields = ('mov_observacion',)
    list_filter = ('mov_tipo', 'mov_fecha')
    inlines = [DetalleMovimientoInline]

    def get_readonly_fields(self, request, obj=None):
        # el tipo no se cambia una vez registrado el movimiento
        return ('mov_tipo',) if obj else ()

    def has_delete_permission(self, request, obj=None):
        # los movimientos son el historial del inventario: no se borran,
        # se corrigen con un movimiento contrario
        return False
