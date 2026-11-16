import datetime
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from detalles_movimiento.models import DetalleMovimiento
from lotes.models import Lote
from movimientos.models import Movimiento
from ubicaciones.models import Ubicacion

Usuario = get_user_model()


def datos(tipo, lineas, fecha='2026-10-01', obs='', existentes=0):
    """Arma el POST del formulario de movimiento. `lineas` es una lista de
    (id_lote, cantidad) o de (id_lote, cantidad, id_detalle, id_mov)."""
    d = {'mov_fecha': fecha, 'mov_tipo': tipo, 'mov_observacion': obs,
         'detalles-TOTAL_FORMS': str(len(lineas)),
         'detalles-INITIAL_FORMS': str(existentes),
         'detalles-MIN_NUM_FORMS': '1', 'detalles-MAX_NUM_FORMS': '1000'}
    for i, linea in enumerate(lineas):
        d[f'detalles-{i}-fk_lot'] = str(linea[0])
        d[f'detalles-{i}-det_cantidad'] = str(linea[1])
        if len(linea) > 2:
            d[f'detalles-{i}-pk_det_id'] = str(linea[2])
            d[f'detalles-{i}-fk_mov'] = str(linea[3])
    return d


class InterfazMovimientosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('crear_roles', stdout=io.StringIO())
        alm = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        ubi = Ubicacion.objects.create(fk_alm=alm, ubi_estante='E1')
        cat = Categoria.objects.create(cat_nombre='Aseo')
        art = Articulo.objects.create(
            fk_cat=cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')
        cls.l1 = Lote.objects.create(fk_art=art, fk_ubi=ubi, lot_codigo='L1')
        cls.l2 = Lote.objects.create(fk_art=art, fk_ubi=ubi, lot_codigo='L2')
        cls.admin = Usuario.objects.create_superuser('root', password='x')
        cls.bodeguero = Usuario.objects.create_user('bode', password='x')
        cls.bodeguero.groups.add(Group.objects.get(name='Bodeguero'))

    def setUp(self):
        self.c = Client()
        self.c.force_login(self.admin)

    def entrada(self, cantidad=100, lote=None, obs=''):
        r = self.c.post(reverse('movimientos:crear'),
                        datos('entrada', [((lote or self.l1).pk, cantidad)], obs=obs))
        self.assertEqual(r.status_code, 302)
        return Movimiento.objects.latest('pk_mov_id')

    # --- acceso
    def test_sin_sesion_redirige_al_login(self):
        for nombre in ('inicio:inicio', 'movimientos:lista', 'movimientos:crear'):
            r = Client().get(reverse(nombre))
            self.assertEqual(r.status_code, 302)
            self.assertIn(reverse('inicio:ingresar'), r.url)

    def test_login_y_logout(self):
        c = Client()
        r = c.post(reverse('inicio:ingresar'), {'username': 'root', 'password': 'x'})
        self.assertRedirects(r, reverse('inicio:inicio'))
        self.assertEqual(c.get(reverse('inicio:inicio')).status_code, 200)
        c.post(reverse('inicio:salir'))
        self.assertEqual(c.get(reverse('inicio:inicio')).status_code, 302)

    def test_bodeguero_registra_pero_no_edita_ni_elimina(self):
        mov = self.entrada()
        b = Client()
        b.force_login(self.bodeguero)
        self.assertEqual(b.get(reverse('movimientos:lista')).status_code, 200)
        self.assertEqual(b.get(reverse('movimientos:crear')).status_code, 200)
        self.assertEqual(b.get(reverse('movimientos:editar', args=[mov.pk])).status_code, 403)
        self.assertEqual(b.get(reverse('movimientos:eliminar', args=[mov.pk])).status_code, 403)
        b.post(reverse('movimientos:crear'), datos('salida', [(self.l1.pk, 10)]))
        self.assertEqual(self.l1.stock, Decimal('90'))

    # --- listar / detalle
    def test_lista_filtra_y_busca(self):
        self.entrada(obs='Compra inicial')
        self.c.post(reverse('movimientos:crear'),
                    datos('salida', [(self.l1.pk, 10)], obs='Despacho'))
        r = self.c.get(reverse('movimientos:lista'))
        self.assertEqual(len(r.context['movimientos']), 2)
        r = self.c.get(reverse('movimientos:lista'), {'tipo': 'salida'})
        self.assertEqual([m.mov_tipo for m in r.context['movimientos']], ['salida'])
        r = self.c.get(reverse('movimientos:lista'), {'q': 'compra'})
        self.assertEqual(len(r.context['movimientos']), 1)

    def test_detalle_muestra_lineas(self):
        mov = self.entrada(40)
        r = self.c.get(reverse('movimientos:detalle', args=[mov.pk]))
        self.assertContains(r, 'L1')
        self.assertContains(r, 'Jabón')

    def test_inicio_muestra_stock(self):
        self.entrada(75)
        r = self.c.get(reverse('inicio:inicio'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '75')

    # --- crear
    def test_crear_entrada_con_varias_lineas(self):
        r = self.c.post(reverse('movimientos:crear'),
                        datos('entrada', [(self.l1.pk, 100), (self.l2.pk, 50)]))
        mov = Movimiento.objects.get()
        self.assertRedirects(r, reverse('movimientos:detalle', args=[mov.pk]))
        self.assertEqual(mov.detalles.count(), 2)
        self.assertEqual(self.l1.stock, Decimal('100'))
        self.assertEqual(self.l2.stock, Decimal('50'))

    def test_salida_sin_stock_se_rechaza_y_no_guarda_nada(self):
        self.entrada(10)
        r = self.c.post(reverse('movimientos:crear'),
                        datos('salida', [(self.l1.pk, 11)]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Stock insuficiente')
        self.assertEqual(Movimiento.objects.count(), 1)
        self.assertEqual(self.l1.stock, Decimal('10'))

    def test_lote_repetido_se_rechaza(self):
        r = self.c.post(reverse('movimientos:crear'),
                        datos('entrada', [(self.l1.pk, 5), (self.l1.pk, 6)]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'solo puede aparecer una vez')
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_cantidad_cero_o_sin_lineas_se_rechaza(self):
        r = self.c.post(reverse('movimientos:crear'),
                        datos('entrada', [(self.l1.pk, 0)]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Movimiento.objects.count(), 0)
        r = self.c.post(reverse('movimientos:crear'), datos('entrada', []))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Movimiento.objects.count(), 0)

    # --- editar
    def test_editar_cantidad_y_observacion_pero_no_el_tipo(self):
        mov = self.entrada(100)
        det = mov.detalles.get()
        r = self.c.post(reverse('movimientos:editar', args=[mov.pk]),
                        datos('salida', [(self.l1.pk, 80, det.pk, mov.pk)],
                              obs='Corregido', existentes=1))
        self.assertRedirects(r, reverse('movimientos:detalle', args=[mov.pk]))
        mov.refresh_from_db()
        self.assertEqual(mov.mov_tipo, 'entrada')      # el intento de cambiar el tipo se ignora
        self.assertEqual(mov.mov_observacion, 'Corregido')
        self.assertEqual(self.l1.stock, Decimal('80'))

    def test_no_se_puede_bajar_una_entrada_ya_consumida(self):
        mov = self.entrada(100)
        self.c.post(reverse('movimientos:crear'), datos('salida', [(self.l1.pk, 90)]))
        det = mov.detalles.get()
        r = self.c.post(reverse('movimientos:editar', args=[mov.pk]),
                        datos('entrada', [(self.l1.pk, 50, det.pk, mov.pk)], existentes=1))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Stock insuficiente')
        self.assertEqual(self.l1.stock, Decimal('10'))

    def test_editar_agrega_y_quita_lineas(self):
        mov = self.entrada(100)
        det = mov.detalles.get()
        d = datos('entrada', [(self.l1.pk, 100, det.pk, mov.pk), (self.l2.pk, 7)], existentes=1)
        r = self.c.post(reverse('movimientos:editar', args=[mov.pk]), d)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(mov.detalles.count(), 2)
        det2 = mov.detalles.get(fk_lot=self.l2)
        d = datos('entrada', [(self.l1.pk, 100, det.pk, mov.pk),
                              (self.l2.pk, 7, det2.pk, mov.pk)], existentes=2)
        d['detalles-1-DELETE'] = 'on'
        r = self.c.post(reverse('movimientos:editar', args=[mov.pk]), d)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(mov.detalles.count(), 1)

    # --- eliminar
    def test_eliminar_pide_confirmacion_y_borra(self):
        mov = self.entrada(100)
        self.c.post(reverse('movimientos:crear'), datos('salida', [(self.l1.pk, 30)]))
        salida = Movimiento.objects.get(mov_tipo='salida')
        r = self.c.get(reverse('movimientos:eliminar', args=[salida.pk]))
        self.assertContains(r, 'Confirmar eliminación')
        self.assertTrue(Movimiento.objects.filter(pk=salida.pk).exists())  # el GET no borra
        r = self.c.post(reverse('movimientos:eliminar', args=[salida.pk]))
        self.assertRedirects(r, reverse('movimientos:lista'))
        self.assertFalse(Movimiento.objects.filter(pk=salida.pk).exists())
        self.assertEqual(self.l1.stock, Decimal('100'))
        self.assertEqual(DetalleMovimiento.objects.count(), 1)

    def test_no_se_elimina_una_entrada_ya_consumida(self):
        mov = self.entrada(100)
        self.c.post(reverse('movimientos:crear'), datos('salida', [(self.l1.pk, 30)]))
        r = self.c.post(reverse('movimientos:eliminar', args=[mov.pk]), follow=True)
        self.assertContains(r, 'Stock insuficiente')
        self.assertTrue(Movimiento.objects.filter(pk=mov.pk).exists())
        self.assertEqual(self.l1.stock, Decimal('70'))
