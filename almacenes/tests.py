from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Almacen


class AlmacenTests(TestCase):
    def test_str(self):
        self.assertEqual(str(Almacen(alm_nombre='Norte')), 'Norte')

    def test_nombre_unico(self):
        Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Almacen.objects.create(alm_nombre='Norte', alm_direccion='y')
