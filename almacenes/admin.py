from django.contrib import admin

from ubicaciones.models import Ubicacion
from .models import Almacen


class UbicacionInline(admin.TabularInline):
    model = Ubicacion
    extra = 1
    show_change_link = True


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('pk_alm_id', 'alm_nombre', 'alm_direccion')
    search_fields = ('alm_nombre', 'alm_direccion')
    list_filter = ('alm_nombre',)
    inlines = [UbicacionInline]
    readonly_fields = ('stock_en_articulos',)

    @admin.display(description='Stock por artículo')
    def stock_en_articulos(self, obj):
        if not obj.pk:
            return '-'
        filas = obj.stock_por_articulo()
        return ' | '.join(f'{n}: {c} {u}' for n, c, u in filas) or 'Sin movimientos'
