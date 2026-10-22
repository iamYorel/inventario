# Sistema de Inventario Multialmacén

Sistema de información hecho con Django para controlar los productos que
entran y salen de las bodegas de una empresa con varios almacenes. Registra
artículos, lotes, el almacén y estante donde está cada lote, y cada movimiento
de entrada o salida. **El stock no se guarda en ninguna columna: se calcula a
partir de los movimientos.** Toda la información se administra desde Django
Admin.

Trabajo del Entregable del Segundo Corte — Ingeniería de Sistemas,
Universidad de La Guajira.

## Requisitos

- Python 3.10 o superior
- Django (versión fijada en `requirements.txt`; no hay otras dependencias)
- Base de datos SQLite (se crea con `migrate`, no requiere instalación)

## Instalación y ejecución

Abrir una terminal en la carpeta que contiene `manage.py` y ejecutar:

```bash
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # Mac / Linux

pip install -r requirements.txt
python manage.py migrate         # aplica las migraciones
python manage.py crear_roles     # crea los grupos de usuarios (ver "Actores")
python manage.py createsuperuser # crea tu usuario administrador
python manage.py cargar_datos_prueba   # opcional: carga los datos de ejemplo
python manage.py runserver
```

Después abrir <http://127.0.0.1:8000/admin/> e iniciar sesión.

- `cargar_datos_prueba` se puede ejecutar varias veces sin duplicar registros y
  no borra nada. Carga los datos de `docs/datos_de_prueba.md` (3 registros por
  tabla). También se pueden ingresar a mano desde el admin siguiendo ese mismo
  documento.
- Si se prefiere, la clave y el modo de depuración se configuran con las
  variables de entorno `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`0` para
  desactivarlo) y `DJANGO_ALLOWED_HOSTS`. Por defecto el proyecto está
  preparado para uso local de desarrollo.

### Credenciales de prueba

El repositorio no contiene contraseñas: cada persona crea su superusuario con
`createsuperuser`. Los usuarios de cada rol los crea el administrador desde
**Autenticación y autorización → Usuarios**, marcando "Es staff" y eligiendo su
grupo.

Superusuario de prueba para la revisión: usuario `admin` (la contraseña se
definió localmente y no se publica por seguridad; si clonas el repo, crea el
tuyo con `createsuperuser`).

## Modelo de datos

Siete tablas, una app de Django por cada una:

| App | Tabla | Descripción |
|---|---|---|
| `almacenes` | `tbl_almacen` | Bodegas de la empresa |
| `ubicaciones` | `tbl_ubicacion` | Estante dentro de un almacén (entidad débil de almacén) |
| `categorias` | `tbl_categoria` | Categorías de artículos |
| `articulos` | `tbl_articulo` | Productos que se manejan |
| `lotes` | `tbl_lote` | Lote de un artículo, ubicado en un estante (entidad débil de artículo) |
| `movimientos` | `tbl_movimiento` | Entradas y salidas de inventario |
| `detalles_movimiento` | `tbl_detalle_movimiento` | Tabla intermedia N:M movimiento–lote, con la cantidad |

Relaciones: almacén 1:N ubicación · categoría 1:N artículo · artículo 1:N lote ·
ubicación 1:N lote · movimiento N:M lote (por `DetalleMovimiento`).

Diagramas en `docs/`: `diagrama_actores.png` (casos de uso) y
`diagrama_er.png` (entidad-relación).

## Cómo funciona el inventario

**Stock = entradas − salidas.** Se calcula sumando `det_cantidad` de los
detalles según el tipo del movimiento (`entrada` / `salida`). El código está en
`detalles_movimiento/stock.py`:

- por lote: `lote.stock`
- por artículo: `articulo.stock`
- por artículo en un almacén: `articulo.stock_en(almacen)` /
  `almacen.stock_de(articulo)`
- por almacén, artículo por artículo: `almacen.stock_por_articulo()` (no se
  suman artículos distintos porque sus unidades no son comparables)

En el admin se ve en la lista de **Lotes** ("Stock actual"), en **Artículos**
("Stock total" y "Stock por almacén") y en **Almacenes** ("Stock por artículo").

### Reglas que protegen el stock

Están en el modelo (`DetalleMovimiento.save()` y una señal para los borrados),
no solo en el admin, y se ejecutan dentro de una transacción: si una regla
falla, no se guarda nada.

- La cantidad de cada detalle debe ser mayor que cero y tener lote.
- Un lote no puede repetirse dentro del mismo movimiento.
- Ninguna operación puede dejar un lote con stock negativo: no se acepta una
  salida mayor a lo disponible, ni bajar o borrar una entrada que ya fue
  consumida.
- El tipo de un movimiento no se cambia una vez registrado.
- Los movimientos no se borran desde el admin: son el historial. Los errores se
  corrigen registrando un movimiento contrario.
- Los lotes involucrados se bloquean con `select_for_update` para evitar
  condiciones de carrera (en SQLite el motor ya escribe de a una operación).

Límite conocido: las operaciones masivas que saltan los métodos de los modelos
(`queryset.update()`, `bulk_create()`) no pasan por estas validaciones.

## Actores y permisos

`python manage.py crear_roles` crea tres grupos con los permisos del diagrama de
casos de uso (principio de mínimo privilegio). Para entrar al admin, el usuario
debe tener "Es staff" marcado.

| Rol | Puede | Solo consulta |
|---|---|---|
| **Administrador** | gestionar almacenes, categorías y usuarios | ubicaciones, artículos, lotes, movimientos (reporte de stock) |
| **Jefe de bodega** | crear y editar artículos, ubicaciones y lotes | almacenes, categorías, historial de movimientos |
| **Bodeguero** | registrar movimientos de entrada y salida (con sus renglones) | lotes, artículos, ubicaciones, almacenes, categorías |

Para probarlo: crear un usuario por rol, iniciar sesión con cada uno y verificar
que el menú del admin solo muestra lo permitido (los demás modelos aparecen sin
botón de agregar o ni aparecen). Las pruebas automáticas de roles están en
`detalles_movimiento/test_roles.py`.

## Pruebas automatizadas

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Cubren: restricciones y relaciones de cada modelo, cálculo del stock (lote,
artículo y almacén), rechazo de salidas sin existencias y de cantidades
inválidas, reglas de integridad al editar o borrar, carga de los datos de
prueba (stock esperado 70, 40 y 15) y permisos de los tres roles.

## Estructura

```
inventario/
├── config/                 # settings.py, urls.py
├── almacenes/  ubicaciones/  categorias/  articulos/
├── lotes/  movimientos/
├── detalles_movimiento/    # modelo, cálculo del stock (stock.py) y
│                           # comandos crear_roles / cargar_datos_prueba
├── docs/                   # diagramas y datos de prueba
├── manage.py
├── requirements.txt
└── README.md
```
