from django.contrib import admin

from .models import Ubicacion


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('pk_ubi_id', 'ubi_estante', 'fk_alm', 'ubi_descripcion')
    search_fields = ('ubi_estante', 'ubi_descripcion', 'fk_alm__alm_nombre')
    list_filter = ('fk_alm',)
