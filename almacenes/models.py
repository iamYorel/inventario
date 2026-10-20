from django.db import models


class Almacen(models.Model):
    pk_alm_id = models.AutoField(primary_key=True)
    alm_nombre = models.CharField(max_length=100, unique=True)
    alm_direccion = models.CharField(max_length=150)

    class Meta:
        db_table = 'tbl_almacen'
        verbose_name = 'almacén'
        verbose_name_plural = 'almacenes'

    def __str__(self):
        return self.alm_nombre

    def stock_de(self, articulo):
        from detalles_movimiento.stock import calcular_stock
        return calcular_stock(fk_lot__fk_art=articulo, fk_lot__fk_ubi__fk_alm=self)

    def stock_por_articulo(self):
        from detalles_movimiento.stock import stock_por_articulo
        return stock_por_articulo(self)
