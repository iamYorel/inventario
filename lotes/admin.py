from django.contrib import admin

from .models import Lote


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('lot_codigo', 'fk_art', 'fk_ubi', 'lot_fecha_vencimiento', 'stock_actual')
    search_fields = ('lot_codigo', 'fk_art__art_nombre', 'fk_art__art_codigo')
    list_filter = ('fk_ubi__fk_alm', 'fk_art', 'lot_fecha_vencimiento')

    @admin.display(description='Stock actual')
    def stock_actual(self, obj):
        return obj.stock
