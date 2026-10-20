import io
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from lotes.models import Lote
from movimientos.models import Movimiento
from ubicaciones.models import Ubicacion

from .models import DetalleMovimiento


class DatosDePruebaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_datos_prueba', stdout=io.StringIO())

    def test_tres_o_mas_registros_por_tabla(self):
        conteos = {
            Categoria: 3, Almacen: 3, Ubicacion: 3, Articulo: 3, Lote: 3,
            Movimiento: 3, DetalleMovimiento: 6,
        }
        for modelo, esperado in conteos.items():
            self.assertEqual(modelo.objects.count(), esperado, modelo.__name__)

    def test_cargar_dos_veces_no_duplica(self):
        call_command('cargar_datos_prueba', stdout=io.StringIO())
        self.assertEqual(Lote.objects.count(), 3)
        self.assertEqual(Movimiento.objects.count(), 3)
        self.assertEqual(DetalleMovimiento.objects.count(), 6)

    def test_stock_esperado_de_los_tres_lotes(self):
        esperado = {'L-2026-01': 70, 'L-2026-02': 40, 'L-2026-03': 15}
        for codigo, stock in esperado.items():
            self.assertEqual(Lote.objects.get(lot_codigo=codigo).stock, Decimal(stock))

    def test_stock_del_articulo_coincide_con_sus_lotes(self):
        for art in Articulo.objects.all():
            suma = sum(l.stock for l in art.lotes.all())
            self.assertEqual(art.stock, suma)
        self.assertEqual(Articulo.objects.get(art_codigo='A001').stock, Decimal('70'))

    def test_stock_por_almacen_y_por_articulo(self):
        norte = Almacen.objects.get(alm_nombre='Norte')
        jabon = Articulo.objects.get(art_codigo='A001')
        self.assertEqual(norte.stock_de(jabon), Decimal('70'))
        self.assertEqual(jabon.stock_en(norte), Decimal('70'))
        self.assertEqual(dict(jabon.stock_por_almacen()), {'Norte': Decimal('70')})
        self.assertEqual(norte.stock_por_articulo(),
                         [('Jabón líquido 1L', Decimal('70'), 'und')])

    def test_relaciones_entre_las_siete_entidades(self):
        lote = Lote.objects.get(lot_codigo='L-2026-01')
        self.assertEqual(lote.fk_art.art_codigo, 'A001')              # artículo 1:N lote
        self.assertEqual(lote.fk_art.fk_cat.cat_nombre, 'Aseo')        # categoría 1:N artículo
        self.assertEqual(lote.fk_ubi.fk_alm.alm_nombre, 'Norte')       # almacén 1:N ubicación
        movs = lote.movimientos.order_by('mov_fecha')                  # N:M vía detalle
        self.assertEqual([m.mov_tipo for m in movs], ['entrada', 'salida'])
        self.assertEqual(lote.detalles.count(), 2)

    def test_los_lotes_viven_en_la_ubicacion_de_su_almacen(self):
        esperado = {'L-2026-01': 'Norte', 'L-2026-02': 'Sur', 'L-2026-03': 'Centro'}
        for codigo, almacen in esperado.items():
            self.assertEqual(
                Lote.objects.get(lot_codigo=codigo).fk_ubi.fk_alm.alm_nombre, almacen)
