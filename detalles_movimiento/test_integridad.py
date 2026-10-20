import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from lotes.models import Lote
from movimientos.models import Movimiento
from ubicaciones.models import Ubicacion

from .models import DetalleMovimiento


class IntegridadTests(TestCase):
    """Las reglas deben cumplirse también fuera del admin (ORM directo)."""

    def setUp(self):
        alm = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        ubi = Ubicacion.objects.create(fk_alm=alm, ubi_estante='E1')
        cat = Categoria.objects.create(cat_nombre='Aseo')
        art = Articulo.objects.create(
            fk_cat=cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')
        self.lote = Lote.objects.create(fk_art=art, fk_ubi=ubi, lot_codigo='L1')

    def mover(self, tipo, cantidad):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo=tipo)
        det = DetalleMovimiento.objects.create(
            fk_mov=mov, fk_lot=self.lote, det_cantidad=Decimal(cantidad))
        return mov, det

    def test_salida_mayor_al_stock_se_rechaza_y_no_deja_rastro(self):
        self.mover('entrada', '10')
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo='salida')
        with self.assertRaises(ValidationError):
            DetalleMovimiento.objects.create(
                fk_mov=mov, fk_lot=self.lote, det_cantidad=Decimal('11'))
        self.assertEqual(DetalleMovimiento.objects.filter(fk_mov=mov).count(), 0)
        self.assertEqual(self.lote.stock, Decimal('10'))

    def test_salida_exacta_al_stock_es_valida(self):
        self.mover('entrada', '10')
        self.mover('salida', '10')
        self.assertEqual(self.lote.stock, 0)

    def test_bajar_una_entrada_ya_consumida_se_rechaza(self):
        _, entrada = self.mover('entrada', '10')
        self.mover('salida', '8')
        entrada.det_cantidad = Decimal('5')  # quedaría 5 - 8 = -3
        with self.assertRaises(ValidationError):
            entrada.save()
        entrada.refresh_from_db()
        self.assertEqual(entrada.det_cantidad, Decimal('10'))

    def test_subir_una_salida_por_encima_del_stock_se_rechaza(self):
        self.mover('entrada', '10')
        _, salida = self.mover('salida', '8')
        salida.det_cantidad = Decimal('11')
        with self.assertRaises(ValidationError):
            salida.save()
        salida.det_cantidad = Decimal('10')  # justo lo disponible: válido
        salida.save()
        self.assertEqual(self.lote.stock, 0)

    def test_borrar_una_entrada_consumida_se_rechaza(self):
        mov, _ = self.mover('entrada', '10')
        self.mover('salida', '4')
        # borrado masivo y borrado en cascada desde el movimiento
        with self.assertRaises(ValidationError), transaction.atomic():
            Movimiento.objects.filter(pk=mov.pk).delete()
        with self.assertRaises(ValidationError), transaction.atomic():
            DetalleMovimiento.objects.filter(fk_mov=mov).delete()
        self.assertTrue(Movimiento.objects.filter(pk=mov.pk).exists())
        self.assertEqual(self.lote.stock, Decimal('6'))

    def test_borrar_una_salida_devuelve_el_stock(self):
        self.mover('entrada', '10')
        mov, _ = self.mover('salida', '4')
        mov.delete()
        self.assertEqual(self.lote.stock, Decimal('10'))

    def test_no_se_puede_cambiar_el_tipo_de_un_movimiento(self):
        mov, _ = self.mover('entrada', '10')
        mov.mov_tipo = 'salida'
        with self.assertRaises(ValidationError):
            mov.save()
        mov.refresh_from_db()
        self.assertEqual(mov.mov_tipo, 'entrada')

    def test_detalle_sin_lote_es_invalido(self):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo='entrada')
        detalle = DetalleMovimiento(fk_mov=mov, det_cantidad=Decimal('1'))
        with self.assertRaises(ValidationError) as ctx:
            detalle.full_clean()
        self.assertIn('fk_lot', ctx.exception.message_dict)

    def test_cantidad_invalida_es_rechazada(self):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo='entrada')
        detalle = DetalleMovimiento(fk_mov=mov, fk_lot=self.lote)
        for valor in (None, Decimal('0'), Decimal('-1')):
            detalle.det_cantidad = valor
            with self.assertRaises(ValidationError):
                detalle.full_clean()
