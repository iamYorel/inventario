from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# a = agregar, c = cambiar, d = eliminar, v = ver
ACCIONES = {'a': 'add', 'c': 'change', 'd': 'delete', 'v': 'view'}

# Permisos por rol, siguiendo el diagrama de casos de uso y el principio de
# mínimo privilegio. Los movimientos nunca se editan ni se borran desde el
# admin (son el historial): las correcciones se hacen con un movimiento contrario.
ROLES = {
    'Administrador': {
        ('almacenes', 'almacen'): 'acdv',     # gestionar almacenes
        ('categorias', 'categoria'): 'acdv',  # gestionar categorías
        ('auth', 'user'): 'acdv',             # gestionar usuarios
        ('auth', 'group'): 'v',
        ('ubicaciones', 'ubicacion'): 'v',    # consultar reporte de stock
        ('articulos', 'articulo'): 'v',
        ('lotes', 'lote'): 'v',
        ('movimientos', 'movimiento'): 'v',
        ('detalles_movimiento', 'detallemovimiento'): 'v',
    },
    'Jefe de bodega': {
        ('articulos', 'articulo'): 'acv',     # gestionar artículos
        ('ubicaciones', 'ubicacion'): 'acv',  # gestionar ubicaciones
        ('lotes', 'lote'): 'acv',             # registrar lote
        ('almacenes', 'almacen'): 'v',        # consultar stock por almacén
        ('categorias', 'categoria'): 'v',
        ('movimientos', 'movimiento'): 'v',   # consultar historial
        ('detalles_movimiento', 'detallemovimiento'): 'v',
    },
    'Bodeguero': {
        ('movimientos', 'movimiento'): 'av',  # registrar entrada / salida
        ('detalles_movimiento', 'detallemovimiento'): 'av',
        ('lotes', 'lote'): 'v',               # consultar stock y ubicación
        ('articulos', 'articulo'): 'v',
        ('ubicaciones', 'ubicacion'): 'v',
        ('almacenes', 'almacen'): 'v',
        ('categorias', 'categoria'): 'v',
    },
}


class Command(BaseCommand):
    help = 'Crea (o actualiza) los grupos Administrador, Jefe de bodega y Bodeguero.'

    def handle(self, *args, **options):
        for nombre, modelos in ROLES.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = [
                Permission.objects.get(content_type__app_label=app,
                                       codename=f'{ACCIONES[letra]}_{modelo}')
                for (app, modelo), letras in modelos.items() for letra in letras
            ]
            grupo.permissions.set(permisos)
            self.stdout.write(f'{nombre}: {len(permisos)} permisos')
