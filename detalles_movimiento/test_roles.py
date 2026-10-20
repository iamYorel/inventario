import datetime
import io

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase

from almacenes.models import Almacen
from articulos.models import Articulo
from categorias.models import Categoria
from lotes.models import Lote
from movimientos.models import Movimiento
from ubicaciones.models import Ubicacion

Usuario = get_user_model()


class RolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('crear_roles', stdout=io.StringIO())
        alm = Almacen.objects.create(alm_nombre='Norte', alm_direccion='x')
        ubi = Ubicacion.objects.create(fk_alm=alm, ubi_estante='E1')
        cat = Categoria.objects.create(cat_nombre='Aseo')
        art = Articulo.objects.create(
            fk_cat=cat, art_codigo='A1', art_nombre='Jabón', art_unidad='und')
        cls.lote = Lote.objects.create(fk_art=art, fk_ubi=ubi, lot_codigo='L1')
        cls.mov = Movimiento.objects.create(
            mov_fecha=datetime.date.today(), mov_tipo='entrada')
        cls.usuarios = {}
        for grupo in ('Administrador', 'Jefe de bodega', 'Bodeguero'):
            u = Usuario.objects.create_user(
                username=grupo.replace(' ', '_').lower(), is_staff=True)
            u.groups.add(Group.objects.get(name=grupo))
            cls.usuarios[grupo] = u

    def cliente(self, grupo):
        c = Client()
        c.force_login(self.usuarios[grupo])
        return c

    def estado(self, grupo, ruta, metodo='get', datos=None):
        c = self.cliente(grupo)
        return getattr(c, metodo)(f'/admin/{ruta}', datos or {}).status_code

    # --- Administrador: almacenes, categorías y usuarios; el resto solo lectura
    def test_administrador(self):
        A = 'Administrador'
        for ruta in ('almacenes/almacen/add/', 'categorias/categoria/add/',
                     'auth/user/add/', 'auth/user/'):
            self.assertEqual(self.estado(A, ruta), 200, ruta)
        for ruta in ('articulos/articulo/add/', 'lotes/lote/add/',
                     'ubicaciones/ubicacion/add/', 'movimientos/movimiento/add/'):
            self.assertEqual(self.estado(A, ruta), 403, ruta)
        for ruta in ('articulos/articulo/', 'lotes/lote/', 'movimientos/movimiento/'):
            self.assertEqual(self.estado(A, ruta), 200, ruta)  # reporte de stock

    # --- Jefe de bodega: artículos, ubicaciones y lotes; el resto lectura
    def test_jefe_de_bodega(self):
        J = 'Jefe de bodega'
        for ruta in ('articulos/articulo/add/', 'ubicaciones/ubicacion/add/',
                     'lotes/lote/add/', 'almacenes/almacen/',
                     'movimientos/movimiento/'):
            self.assertEqual(self.estado(J, ruta), 200, ruta)
        for ruta in ('almacenes/almacen/add/', 'categorias/categoria/add/',
                     'movimientos/movimiento/add/', 'auth/user/'):
            self.assertEqual(self.estado(J, ruta), 403, ruta)
        self.assertEqual(
            self.estado(J, f'articulos/articulo/{self.lote.fk_art_id}/delete/'), 403)

    # --- Bodeguero: solo registra movimientos y consulta
    def test_bodeguero(self):
        B = 'Bodeguero'
        for ruta in ('movimientos/movimiento/add/', 'lotes/lote/',
                     'articulos/articulo/', 'ubicaciones/ubicacion/'):
            self.assertEqual(self.estado(B, ruta), 200, ruta)
        for ruta in ('almacenes/almacen/add/', 'articulos/articulo/add/',
                     'lotes/lote/add/', 'auth/user/'):
            self.assertEqual(self.estado(B, ruta), 403, ruta)

    def test_bodeguero_puede_registrar_una_entrada_pero_no_editarla_ni_borrarla(self):
        B = 'Bodeguero'
        datos = {
            'mov_fecha': '2026-10-01', 'mov_tipo': 'entrada', 'mov_observacion': '',
            'detalles-TOTAL_FORMS': '1', 'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0', 'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-fk_lot': str(self.lote.pk), 'detalles-0-det_cantidad': '10',
        }
        antes = Movimiento.objects.count()
        self.assertEqual(self.estado(B, 'movimientos/movimiento/add/', 'post', datos), 302)
        self.assertEqual(Movimiento.objects.count(), antes + 1)
        self.assertEqual(self.lote.stock, 10)
        ruta = f'movimientos/movimiento/{self.mov.pk}/'
        self.assertEqual(self.estado(B, ruta + 'change/', 'post', datos), 403)
        self.assertEqual(self.estado(B, ruta + 'delete/'), 403)

    def test_bodeguero_no_puede_sacar_mas_de_lo_que_hay(self):
        B = 'Bodeguero'
        datos = {
            'mov_fecha': '2026-10-02', 'mov_tipo': 'salida', 'mov_observacion': '',
            'detalles-TOTAL_FORMS': '1', 'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0', 'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-fk_lot': str(self.lote.pk), 'detalles-0-det_cantidad': '5',
        }
        antes = Movimiento.objects.count()
        c = self.cliente(B)
        r = c.post('/admin/movimientos/movimiento/add/', datos)
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con el error
        self.assertIn('Stock insuficiente', r.content.decode())
        self.assertEqual(Movimiento.objects.count(), antes)

    def test_nadie_borra_movimientos_desde_el_admin(self):
        ruta = f'movimientos/movimiento/{self.mov.pk}/delete/'
        superusuario = Usuario.objects.create_superuser('root', password='clave-de-prueba')
        c = Client()
        c.force_login(superusuario)
        self.assertEqual(c.get('/admin/' + ruta).status_code, 403)

    def test_staff_sin_grupo_no_tiene_permisos(self):
        sin_rol = Usuario.objects.create_user('sin_rol', is_staff=True)
        c = Client()
        c.force_login(sin_rol)
        self.assertEqual(c.get('/admin/almacenes/almacen/add/').status_code, 403)
        self.assertEqual(c.get('/admin/lotes/lote/').status_code, 403)

    def test_usuario_no_staff_es_enviado_al_login(self):
        u = Usuario.objects.create_user('no_staff')
        u.groups.add(Group.objects.get(name='Bodeguero'))
        c = Client()
        c.force_login(u)
        self.assertEqual(c.get('/admin/lotes/lote/').status_code, 302)

    def test_crear_roles_es_repetible(self):
        call_command('crear_roles', stdout=io.StringIO())
        self.assertEqual(Group.objects.count(), 3)
