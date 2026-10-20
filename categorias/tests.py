from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Categoria


class CategoriaTests(TestCase):
    def test_nombre_unico(self):
        Categoria.objects.create(cat_nombre='Aseo')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Categoria.objects.create(cat_nombre='Aseo')
