# Datos de prueba para ingresar en el admin

> Estos datos se pueden cargar automáticamente con `python manage.py cargar_datos_prueba` (sin duplicar si se ejecuta varias veces), o ingresarse a mano desde el admin siguiendo este documento.

Ingrésalos en este orden (cada uno depende del anterior). Son 7 tablas con mínimo 3 registros cada una.
Puedes cambiar nombres y direcciones por los que quieras, pero respeta las relaciones.

## 1. Categorías (3)
| cat_nombre |
|---|
| Aseo |
| Papelería |
| Herramientas |

## 2. Almacenes (3)
| alm_nombre | alm_direccion |
|---|---|
| Norte | Zona industrial, bodega 1 |
| Sur | Zona industrial, bodega 2 |
| Centro | Sector comercial, local 5 |

## 3. Ubicaciones (3) — se agregan dentro de cada almacén
| Almacén | ubi_estante | ubi_descripcion |
|---|---|---|
| Norte | Estante 1 | Pasillo A |
| Sur | Estante 2 | Pasillo B |
| Centro | Estante 1 | Entrada |

## 4. Artículos (3)
| art_codigo | art_nombre | Categoría | art_unidad |
|---|---|---|---|
| A001 | Jabón líquido 1L | Aseo | und |
| P001 | Resma de papel carta | Papelería | resma |
| H001 | Martillo | Herramientas | und |

## 5. Lotes (3) — se agregan dentro de cada artículo
| Artículo | lot_codigo | Ubicación | lot_fecha_vencimiento |
|---|---|---|---|
| A001 | L-2026-01 | Estante 1 - Norte | 2027-06-30 |
| P001 | L-2026-02 | Estante 2 - Sur | (vacío) |
| H001 | L-2026-03 | Estante 1 - Centro | (vacío) |

## 6. Movimientos (3) y 7. Detalles (6) — los detalles van dentro del movimiento
Regístralos en el orden 1, 2, 3: el sistema rechaza una salida si no hay stock suficiente, así que la entrada va primero.
| Movimiento | mov_fecha | mov_tipo | mov_observacion | Detalles (lote → cantidad) |
|---|---|---|---|---|
| 1 | 2026-10-01 | entrada | Compra inicial | L-2026-01 → 100 · L-2026-02 → 50 · L-2026-03 → 20 |
| 2 | 2026-10-05 | salida | Despacho a oficina | L-2026-01 → 30 |
| 3 | 2026-10-08 | salida | Uso en mantenimiento | L-2026-02 → 10 · L-2026-03 → 5 |

## Stock esperado (para comprobar que el cálculo funciona)
| Lote | Cálculo | Stock |
|---|---|---|
| L-2026-01 | 100 − 30 | **70** |
| L-2026-02 | 50 − 10 | **40** |
| L-2026-03 | 20 − 5 | **15** |

Se ve en el admin: lista de Lotes (columna "Stock actual") y lista de Artículos ("Stock total").
