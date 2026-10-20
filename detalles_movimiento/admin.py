from django.contrib import admin

from .models import DetalleMovimiento


@admin.register(DetalleMovimiento)
class DetalleMovimientoAdmin(admin.ModelAdmin):
    list_display = ('pk_det_id', 'fk_mov', 'fk_lot', 'det_cantidad')
    search_fields = ('fk_lot__lot_codigo', 'fk_lot__fk_art__art_nombre')
    list_filter = ('fk_mov__mov_tipo',)

    def has_delete_permission(self, request, obj=None):
        return False
