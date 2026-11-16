# Sistema de Inventario Multialmacén

## Descripción

Sistema de información hecho con Django para controlar los productos que
entran y salen de las bodegas de una empresa con varios almacenes. Registra
artículos, lotes, el almacén y estante donde está cada lote, y cada movimiento
de entrada o salida. **El stock no se guarda en ninguna columna: se calcula a
partir de los movimientos.**

Está pensado para tres actores: **Administrador**, **Jefe de bodega** y
**Bodeguero**. Los catálogos (almacenes, categorías, artículos, ubicaciones y
lotes) se administran desde el panel de administración de Django; el proceso
principal, **registrar movimientos de inventario**, tiene su propia interfaz web.

## Integrantes

- Christian Alvarez – alvarezchristiandaniel-creator
- Yorel Díaz – iamYorel
- Jackson Almazo – jackjavier-23

## Tecnologías

- Django 6.1.2 (Python 3.10 o superior), base de datos SQLite
- Bootstrap 5.3.3 y Bootstrap Icons 1.11.3 como framework de CSS, **incluidos
  por CDN** (jsDelivr) en `templates/base.html`; no se instala nada con pip.
  Requiere conexión a internet para ver los estilos.
- Paleta de colores propia en `static/css/inventario.css`: azul marino
  (identidad), azul acero (enlaces), ámbar (acento) y verde azulado / coral
  para entradas y salidas.

## Tablas principales

| Tabla | Descripción |
| --- | --- |
| `tbl_almacen` | Bodegas de la empresa |
| `tbl_ubicacion` | Estante dentro de un almacén (entidad débil de almacén) |
| `tbl_categoria` | Categorías de artículos |
| `tbl_articulo` | Productos que se manejan; `art_usa_lote` indica si se manejan por lotes o solo por cantidad |
| `tbl_lote` | Lote de un artículo, ubicado en un estante (entidad débil de artículo) |
| `tbl_movimiento` | Entradas y salidas de inventario |
| `tbl_detalle_movimiento` | Tabla intermedia N:M movimiento–lote, con la cantidad |

Una app de Django por cada tabla (`almacenes`, `ubicaciones`, `categorias`,
`articulos`, `lotes`, `movimientos`, `detalles_movimiento`) más la app `inicio`
(panel de inicio e inicio de sesión).

Relaciones: almacén 1:N ubicación · categoría 1:N artículo · artículo 1:N lote ·
ubicación 1:N lote · movimiento N:M lote (por `DetalleMovimiento`).

**Artículos sin lotes:** si `art_usa_lote` es falso, el artículo se cuenta solo
por cantidad. Por convención se le registra un único lote (por ejemplo,
"SIN-LOTE"), de modo que todo movimiento siga apuntando a un lote y el stock
se calcule igual.

## Diagramas

- Actores: docs/diagrama_actores.png
- Entidad-relación: docs/diagrama_er.png

## Funcionalidades

**Proceso con CRUD completo: movimientos de inventario** (tablas
`tbl_movimiento` + `tbl_detalle_movimiento` + `tbl_lote`). Un movimiento se
registra con fecha, tipo y varias líneas (lote + cantidad).

| Acción | Ruta | Permiso de Django |
| --- | --- | --- |
| Listar (filtro por tipo, búsqueda, paginación) | `/movimientos/` | `view_movimiento` |
| Crear | `/movimientos/nuevo/` | `add_movimiento` |
| Detalle | `/movimientos/<id>/` | `view_movimiento` |
| Editar | `/movimientos/<id>/editar/` | `change_movimiento` |
| Eliminar (con confirmación) | `/movimientos/<id>/eliminar/` | `delete_movimiento` |

Funcionalidades adicionales:

- Inicio y cierre de sesión (`/ingresar/`, `/salir/`).
- Roles y permisos: cada rol ve y hace solo lo que le corresponde. Las rutas
  están protegidas con `LoginRequiredMixin` y `PermissionRequiredMixin`; sin
  sesión se redirige al login y sin permiso se muestra una página 403.
- Panel de inicio (`/`) con totales, stock actual por lote y últimos movimientos.
- Validaciones con mensajes de error y de confirmación: stock insuficiente,
  cantidades mayores que cero, lote repetido en un movimiento.
- El panel de administración (`/admin/`) sigue funcionando como en el segundo corte.

## Cómo ejecutar el proyecto

1. git clone https://github.com/iamYorel/inventario.git
2. python -m venv venv
3. venv\Scripts\activate   (Linux/macOS: source venv/bin/activate)
4. pip install -r requirements.txt
5. python manage.py migrate
6. python manage.py runserver

El repositorio incluye `db.sqlite3` con datos de prueba y usuarios ya creados,
así que basta con esos pasos y abrir <http://127.0.0.1:8000/>.

Para empezar con una base de datos vacía: borrar `db.sqlite3`, ejecutar
`migrate`, `crear_roles`, `cargar_datos_prueba` y `crear_usuarios_prueba` (o
`createsuperuser` para tu propio administrador).

## Usuarios de prueba

Clave de todos: `Inventario2026*` (solo para demostración).

| Usuario | Rol | Qué puede hacer en la interfaz |
| --- | --- | --- |
| `admin` | Superusuario del admin | Todo: CRUD completo de movimientos y panel de administración |
| `administrador` | Administrador | Consultar movimientos y stock; gestiona almacenes, categorías y usuarios en el admin |
| `jefe` | Jefe de bodega | Consultar movimientos y stock; gestiona artículos, ubicaciones y lotes en el admin |
| `bodeguero` | Bodeguero | Consultar y **registrar** entradas y salidas |

Editar y eliminar movimientos exige permisos que ningún rol operativo tiene
(los movimientos son el historial: las correcciones normales se hacen con un
movimiento contrario); se hacen con `admin`.

## Modelo de datos y reglas del inventario

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
prueba (stock esperado 70, 40 y 15), permisos de los tres roles en el admin y
el CRUD de movimientos desde la interfaz (acceso, listar, crear, editar,
eliminar y validaciones).

## Estructura

```
inventario/
├── config/                 # settings.py, urls.py
├── almacenes/  ubicaciones/  categorias/  articulos/  lotes/
├── movimientos/            # modelo, formularios, vistas y urls.py del CRUD
├── detalles_movimiento/    # modelo, cálculo del stock (stock.py) y comandos
│                           # crear_roles / cargar_datos_prueba / crear_usuarios_prueba
├── inicio/                 # panel de inicio, login y logout
├── templates/              # base.html + plantillas por app (inicio/, movimientos/)
├── static/css/             # paleta de colores (inventario.css)
├── docs/                   # diagramas y datos de prueba
├── db.sqlite3              # base de datos con datos de prueba
├── manage.py
├── requirements.txt
└── README.md
```
