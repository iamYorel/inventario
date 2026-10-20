from django.contrib import admin

from lotes.models import Lote
from .models import Articulo


class LoteInline(admin.TabularInline):
    model = Lote
    extra = 1
    show_change_link = True


@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = ('art_codigo', 'art_nombre', 'fk_cat', 'art_unidad', 'stock_total')
    search_fields = ('art_codigo', 'art_nombre', 'fk_cat__cat_nombre')
    list_filter = ('fk_cat', 'art_unidad')
    inlines = [LoteInline]
    readonly_fields = ('stock_total', 'stock_en_almacenes')

    @admin.display(description='Stock total')
    def stock_total(self, obj):
        return obj.stock if obj.pk else '-'

    @admin.display(description='Stock por almacén')
    def stock_en_almacenes(self, obj):
        if not obj.pk:
            return '-'
        filas = obj.stock_por_almacen()
        return ' | '.join(f'{nombre}: {cant}' for nombre, cant in filas) or 'Sin movimientos'
