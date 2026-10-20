from django.db import models


class Articulo(models.Model):
    pk_art_id = models.AutoField(primary_key=True)
    fk_cat = models.ForeignKey(
        'categorias.Categoria', on_delete=models.PROTECT,
        db_column='fk_cat_id', related_name='articulos',
        verbose_name='categoría',
    )
    art_codigo = models.CharField(max_length=30, unique=True)
    art_nombre = models.CharField(max_length=100)
    art_unidad = models.CharField(max_length=20)

    class Meta:
        db_table = 'tbl_articulo'
        verbose_name = 'artículo'
        verbose_name_plural = 'artículos'

    def __str__(self):
        return f'{self.art_codigo} - {self.art_nombre}'

    @property
    def stock(self):
        from detalles_movimiento.stock import calcular_stock
        return calcular_stock(fk_lot__fk_art=self)

    def stock_en(self, almacen):
        from detalles_movimiento.stock import calcular_stock
        return calcular_stock(fk_lot__fk_art=self, fk_lot__fk_ubi__fk_alm=almacen)

    def stock_por_almacen(self):
        from detalles_movimiento.stock import stock_por_almacen
        return stock_por_almacen(self)
