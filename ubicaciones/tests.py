from django.db import IntegrityError, transaction
from django.test import TestCase

from almacenes.models import Almacen

from .models import Ubicacion


class UbicacionTests(TestCase):
    def setUp(self):
        self.norte = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        self.sur = Almacen.objects.create(alm_nombre='Sur', alm_direccion='y')

    def test_estante_no_se_repite_en_el_mismo_almacen(self):
        Ubicacion.objects.create(fk_alm=self.norte, ubi_estante='E1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ubicacion.objects.create(fk_alm=self.norte, ubi_estante='E1')

    def test_mismo_estante_en_otro_almacen_es_valido(self):
        Ubicacion.objects.create(fk_alm=self.norte, ubi_estante='E1')
        Ubicacion.objects.create(fk_alm=self.sur, ubi_estante='E1')
        self.assertEqual(Ubicacion.objects.count(), 2)

    def test_entidad_debil_se_borra_con_su_almacen(self):
        Ubicacion.objects.create(fk_alm=self.norte, ubi_estante='E1')
        self.norte.delete()
        self.assertEqual(Ubicacion.objects.count(), 0)
