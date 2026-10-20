import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from detalles_movimiento.models import DetalleMovimiento
from lotes.models import Lote
from movimientos.models import Movimiento
from ubicaciones.models import Ubicacion

CATEGORIAS = ['Aseo', 'Papelería', 'Herramientas']
ALMACENES = [('Norte', 'Zona industrial, bodega 1'),
             ('Sur', 'Zona industrial, bodega 2'),
             ('Centro', 'Sector comercial, local 5')]
UBICACIONES = [('Norte', 'Estante 1', 'Pasillo A'),
               ('Sur', 'Estante 2', 'Pasillo B'),
               ('Centro', 'Estante 1', 'Entrada')]
ARTICULOS = [('A001', 'Jabón líquido 1L', 'Aseo', 'und'),
             ('P001', 'Resma de papel carta', 'Papelería', 'resma'),
             ('H001', 'Martillo', 'Herramientas', 'und')]
# (artículo, código de lote, almacén, estante, vencimiento)
LOTES = [('A001', 'L-2026-01', 'Norte', 'Estante 1', datetime.date(2027, 6, 30)),
         ('P001', 'L-2026-02', 'Sur', 'Estante 2', None),
         ('H001', 'L-2026-03', 'Centro', 'Estante 1', None)]
# (fecha, tipo, observación, [(código de lote, cantidad)]): las entradas van primero
MOVIMIENTOS = [
    (datetime.date(2026, 10, 1), 'entrada', 'Compra inicial',
     [('L-2026-01', 100), ('L-2026-02', 50), ('L-2026-03', 20)]),
    (datetime.date(2026, 10, 5), 'salida', 'Despacho a oficina',
     [('L-2026-01', 30)]),
    (datetime.date(2026, 10, 8), 'salida', 'Uso en mantenimiento',
     [('L-2026-02', 10), ('L-2026-03', 5)]),
]


class Command(BaseCommand):
    help = ('Carga los datos de prueba de docs/datos_de_prueba.md. Se puede '
            'ejecutar varias veces sin duplicar registros y no borra nada.')

    @transaction.atomic
    def handle(self, *args, **options):
        for nombre in CATEGORIAS:
            Categoria.objects.get_or_create(cat_nombre=nombre)
        for nombre, direccion in ALMACENES:
            Almacen.objects.get_or_create(
                alm_nombre=nombre, defaults={'alm_direccion': direccion})
        for almacen, estante, descripcion in UBICACIONES:
            Ubicacion.objects.get_or_create(
                fk_alm=Almacen.objects.get(alm_nombre=almacen), ubi_estante=estante,
                defaults={'ubi_descripcion': descripcion})
        for codigo, nombre, categoria, unidad in ARTICULOS:
            Articulo.objects.get_or_create(
                art_codigo=codigo,
                defaults={'art_nombre': nombre, 'art_unidad': unidad,
                          'fk_cat': Categoria.objects.get(cat_nombre=categoria)})
        for articulo, codigo, almacen, estante, vence in LOTES:
            ubicacion = Ubicacion.objects.get(
                fk_alm__alm_nombre=almacen, ubi_estante=estante)
            Lote.objects.get_or_create(
                fk_art=Articulo.objects.get(art_codigo=articulo), lot_codigo=codigo,
                defaults={'fk_ubi': ubicacion, 'lot_fecha_vencimiento': vence})
        for fecha, tipo, observacion, detalles in MOVIMIENTOS:
            movimiento, _ = Movimiento.objects.get_or_create(
                mov_fecha=fecha, mov_tipo=tipo, mov_observacion=observacion)
            for codigo, cantidad in detalles:
                DetalleMovimiento.objects.get_or_create(
                    fk_mov=movimiento, fk_lot=Lote.objects.get(lot_codigo=codigo),
                    defaults={'det_cantidad': Decimal(cantidad)})
        self.stdout.write(self.style.SUCCESS('Datos de prueba cargados.'))
