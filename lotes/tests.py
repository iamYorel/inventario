from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from ubicaciones.models import Ubicacion

from .models import Lote


class LoteTests(TestCase):
    def setUp(self):
        alm = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        self.ubi = Ubicacion.objects.create(fk_alm=alm, ubi_estante='E1')
        cat = Categoria.objects.create(cat_nombre='Aseo')
        self.art = Articulo.objects.create(
            fk_cat=cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')

    def test_codigo_de_lote_unico_por_articulo(self):
        Lote.objects.create(fk_art=self.art, fk_ubi=self.ubi, lot_codigo='L1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lote.objects.create(fk_art=self.art, fk_ubi=self.ubi, lot_codigo='L1')

    def test_fecha_de_vencimiento_es_opcional(self):
        lote = Lote.objects.create(fk_art=self.art, fk_ubi=self.ubi, lot_codigo='L1')
        self.assertIsNone(lote.lot_fecha_vencimiento)

    def test_no_se_borra_ubicacion_con_lotes(self):
        Lote.objects.create(fk_art=self.art, fk_ubi=self.ubi, lot_codigo='L1')
        with self.assertRaises(ProtectedError):
            self.ubi.delete()
