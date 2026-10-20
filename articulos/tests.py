from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from almacenes.models import Almacen
from categorias.models import Categoria
from lotes.models import Lote
from ubicaciones.models import Ubicacion

from .models import Articulo


class ArticuloTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(cat_nombre='Aseo')
        self.art = Articulo.objects.create(
            fk_cat=self.cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')

    def test_codigo_unico(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Articulo.objects.create(
                fk_cat=self.cat, art_codigo='A1', art_nombre='Otro', art_unidad='und')

    def test_no_se_borra_categoria_con_articulos(self):
        with self.assertRaises(ProtectedError):
            self.cat.delete()

    def test_lotes_son_entidad_debil_del_articulo(self):
        alm = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        ubi = Ubicacion.objects.create(fk_alm=alm, ubi_estante='E1')
        Lote.objects.create(fk_art=self.art, fk_ubi=ubi, lot_codigo='L1')
        self.art.delete()
        self.assertEqual(Lote.objects.count(), 0)
