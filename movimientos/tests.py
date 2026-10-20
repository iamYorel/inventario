import datetime
from decimal import Decimal

from django.forms import inlineformset_factory
from django.test import TestCase

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from detalles_movimiento.models import DetalleMovimiento
from lotes.models import Lote
from ubicaciones.models import Ubicacion

from .forms import DetalleMovimientoFormSet
from .models import Movimiento

FormSet = inlineformset_factory(
    Movimiento, DetalleMovimiento, formset=DetalleMovimientoFormSet,
    fields=('fk_lot', 'det_cantidad'), extra=1)


def datos_nuevo(lote, cantidad):
    return {
        'detalles-TOTAL_FORMS': '1', 'detalles-INITIAL_FORMS': '0',
        'detalles-MIN_NUM_FORMS': '0', 'detalles-MAX_NUM_FORMS': '1000',
        'detalles-0-fk_lot': str(lote.pk), 'detalles-0-det_cantidad': cantidad,
    }


class MovimientoTests(TestCase):
    def setUp(self):
        alm = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        ubi = Ubicacion.objects.create(fk_alm=alm, ubi_estante='E1')
        cat = Categoria.objects.create(cat_nombre='Aseo')
        art = Articulo.objects.create(
            fk_cat=cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')
        self.lote = Lote.objects.create(fk_art=art, fk_ubi=ubi, lot_codigo='L1')

    def movimiento(self, tipo, cantidad):
        mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo=tipo)
        det = DetalleMovimiento.objects.create(
            fk_mov=mov, fk_lot=self.lote, det_cantidad=Decimal(cantidad))
        return mov, det

    def test_relacion_n_m_con_lote_a_traves_del_detalle(self):
        mov, _ = self.movimiento('entrada', '10')
        self.assertEqual(list(mov.lotes.all()), [self.lote])
        self.assertEqual(list(self.lote.movimientos.all()), [mov])

    def test_salida_mayor_al_stock_es_rechazada(self):
        self.movimiento('entrada', '10')
        nuevo = Movimiento(mov_fecha=datetime.date.today(), mov_tipo='salida')
        fs = FormSet(datos_nuevo(self.lote, '11'), instance=nuevo)
        self.assertFalse(fs.is_valid())
        self.assertIn('Stock insuficiente', fs.non_form_errors()[0])

    def test_salida_dentro_del_stock_es_valida(self):
        self.movimiento('entrada', '10')
        nuevo = Movimiento(mov_fecha=datetime.date.today(), mov_tipo='salida')
        fs = FormSet(datos_nuevo(self.lote, '10'), instance=nuevo)
        self.assertTrue(fs.is_valid(), fs.errors)

    def test_una_entrada_nunca_se_bloquea(self):
        nuevo = Movimiento(mov_fecha=datetime.date.today(), mov_tipo='entrada')
        fs = FormSet(datos_nuevo(self.lote, '500'), instance=nuevo)
        self.assertTrue(fs.is_valid(), fs.errors)

    def test_editar_una_salida_no_cuenta_dos_veces_su_propia_cantidad(self):
        self.movimiento('entrada', '10')
        mov, det = self.movimiento('salida', '8')
        datos = {
            'detalles-TOTAL_FORMS': '1', 'detalles-INITIAL_FORMS': '1',
            'detalles-MIN_NUM_FORMS': '0', 'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-pk_det_id': str(det.pk), 'detalles-0-fk_mov': str(mov.pk),
            'detalles-0-fk_lot': str(self.lote.pk), 'detalles-0-det_cantidad': '10',
        }
        fs = FormSet(datos, instance=mov)
        self.assertTrue(fs.is_valid(), fs.errors)
