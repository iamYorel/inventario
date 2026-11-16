from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

CLAVE = 'Inventario2026*'
# (usuario, grupo; None = superusuario)
USUARIOS = [
    ('admin', None),
    ('administrador', 'Administrador'),
    ('jefe', 'Jefe de bodega'),
    ('bodeguero', 'Bodeguero'),
]


class Command(BaseCommand):
    help = ('Crea (o actualiza) un usuario de prueba por rol y un superusuario, '
            'todos con la misma clave de demostración. Solo para desarrollo.')

    def handle(self, *args, **options):
        Usuario = get_user_model()
        for nombre, grupo in USUARIOS:
            usuario, _ = Usuario.objects.get_or_create(username=nombre)
            usuario.is_staff = True
            usuario.is_superuser = grupo is None
            usuario.set_password(CLAVE)
            usuario.save()
            if grupo:
                usuario.groups.set([Group.objects.get(name=grupo)])
            self.stdout.write(f'{nombre} ({grupo or "superusuario"})')
        self.stdout.write(f'Clave de todos: {CLAVE}')
