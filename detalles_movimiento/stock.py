from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import DetalleMovimiento

CERO = Decimal('0.00')


def calcular_stock(**filtros):
    """Entradas - salidas de los detalles que cumplan los filtros."""
    r = DetalleMovimiento.objects.filter(**filtros).aggregate(
        entradas=Sum('det_cantidad', filter=Q(fk_mov__mov_tipo='entrada')),
        salidas=Sum('det_cantidad', filter=Q(fk_mov__mov_tipo='salida')),
    )
    return (r['entradas'] or CERO) - (r['salidas'] or CERO)


def stock_por_almacen(articulo):
    """Lista de (nombre del almacén, stock) para un artículo."""
    almacenes = (
        DetalleMovimiento.objects
        .filter(fk_lot__fk_art=articulo)
        .values_list('fk_lot__fk_ubi__fk_alm__pk_alm_id',
                     'fk_lot__fk_ubi__fk_alm__alm_nombre')
        .distinct()
    )
    return [
        (nombre, calcular_stock(fk_lot__fk_art=articulo,
                                fk_lot__fk_ubi__fk_alm=pk))
        for pk, nombre in almacenes
    ]


def stock_por_articulo(almacen):
    """Lista de (nombre del artículo, stock, unidad) para un almacén.

    No se suman artículos distintos entre sí porque sus unidades no son
    comparables (unidades, resmas, litros...).
    """
    articulos = (
        DetalleMovimiento.objects
        .filter(fk_lot__fk_ubi__fk_alm=almacen)
        .values_list('fk_lot__fk_art__pk_art_id', 'fk_lot__fk_art__art_nombre',
                     'fk_lot__fk_art__art_unidad')
        .distinct()
    )
    return [
        (nombre, calcular_stock(fk_lot__fk_art=pk,
                                fk_lot__fk_ubi__fk_alm=almacen), unidad)
        for pk, nombre, unidad in articulos
    ]


def verificar_stock_no_negativo(ids_lotes):
    """Lanza ValidationError si algún lote quedaría con stock negativo.

    Se llama dentro de una transacción: si falla, se revierte el cambio.
    """
    from lotes.models import Lote
    for pk in ids_lotes:
        stock = calcular_stock(fk_lot=pk)
        if stock < 0:
            raise ValidationError(
                f'Stock insuficiente en {Lote.objects.get(pk=pk)}: '
                f'la operación dejaría el stock en {stock}.')


def lotes_con_stock():
    """Lotes con el atributo `stock_calc` (entradas - salidas) calculado en
    una sola consulta, para listados y selectores sin una consulta por lote."""
    from lotes.models import Lote
    campo = DecimalField(max_digits=12, decimal_places=2)
    cero = Value(CERO, output_field=campo)
    entradas = Coalesce(
        Sum('detalles__det_cantidad',
            filter=Q(detalles__fk_mov__mov_tipo='entrada')),
        cero, output_field=campo)
    salidas = Coalesce(
        Sum('detalles__det_cantidad',
            filter=Q(detalles__fk_mov__mov_tipo='salida')),
        cero, output_field=campo)
    return (Lote.objects.select_related('fk_art', 'fk_ubi__fk_alm')
            .annotate(stock_calc=entradas - salidas))
