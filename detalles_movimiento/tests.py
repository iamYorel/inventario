import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from lotes.models import Lote
from movimientos.models import Movimiento
from ubicaciones.models import Ubicacion

from .models import DetalleMovimiento


class StockTests(TestCase):
    def setUp(self):
        self.norte = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        self.sur = Almacen.objects.create(alm_nombre='Sur', alm_direccion='y')
        self.ubi_norte = Ubicacion.objects.create(fk_alm=self.norte, ubi_estante='E1')
        self.ubi_sur = Ubicacion.objects.create(fk_alm=self.sur, ubi_estante='E2')
        cat = Categoria.objects.create(cat_nombre='Aseo')
        self.art = Articulo.objects.create(
            fk_cat=cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')
        self.lote_norte = Lote.objects.create(
            fk_art=self.art, fk_ubi=self.ubi_norte, lot_codigo='L1')
        self.lote_sur = Lote.objects.create(
            fk_art=self.art, fk_ubi=self.ubi_sur, lot_codigo='L2')

    def mover(self, tipo, lote, cantidad):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo=tipo)
        DetalleMovimiento.objects.create(
            fk_mov=mov, fk_lot=lote, det_cantidad=Decimal(cantidad))

    def test_lote_sin_movimientos_tiene_stock_cero(self):
        self.assertEqual(self.lote_norte.stock, 0)

    def test_entrada_10_y_salida_3_da_7(self):
        self.mover('entrada', self.lote_norte, '10')
        self.mover('salida', self.lote_norte, '3')
        self.assertEqual(self.lote_norte.stock, Decimal('7'))

    def test_stock_del_articulo_suma_todos_sus_lotes(self):
        self.mover('entrada', self.lote_norte, '10')
        self.mover('entrada', self.lote_sur, '20')
        self.mover('salida', self.lote_sur, '5')
        self.assertEqual(self.art.stock, Decimal('25'))

    def test_stock_por_almacen(self):
        self.mover('entrada', self.lote_norte, '10')
        self.mover('salida', self.lote_norte, '3')
        self.mover('entrada', self.lote_sur, '20')
        self.assertEqual(self.art.stock_en(self.norte), Decimal('7'))
        self.assertEqual(self.art.stock_en(self.sur), Decimal('20'))
        self.assertEqual(
            dict(self.art.stock_por_almacen()),
            {'Norte': Decimal('7'), 'Sur': Decimal('20')})

    def test_cantidad_cero_o_negativa_es_rechazada(self):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo='entrada')
        for cantidad in ('0', '-5'):
            detalle = DetalleMovimiento(
                fk_mov=mov, fk_lot=self.lote_norte, det_cantidad=Decimal(cantidad))
            with self.assertRaises(ValidationError):
                detalle.full_clean()

    def test_lote_no_se_repite_en_el_mismo_movimiento(self):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo='entrada')
        DetalleMovimiento.objects.create(
            fk_mov=mov, fk_lot=self.lote_norte, det_cantidad=Decimal('1'))
        with self.assertRaises(IntegrityError), transaction.atomic():
            DetalleMovimiento.objects.create(
                fk_mov=mov, fk_lot=self.lote_norte, det_cantidad=Decimal('2'))
