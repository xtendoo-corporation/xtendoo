# Xtendoo Stock Barcode

MVP backend-first para Odoo 19 que introduce un flujo de escaneo clásico en
`stock.picking` con flujo clásico y un uso mínimo de JS solo para el menú principal escaneable.

## Objetivo

Ofrecer una primera versión funcional inspirada en `stock_barcode`, pero con una
arquitectura mucho más simple y basada en:

- `barcodes.barcode_events_mixin`
- `widget="barcode_handler"`
- lógica Python sobre `stock.picking`
- vista formulario clásica

## Alcance actual

Incluye:

- app raíz `Xtendoo Barcode` visible en el menú inicial de Odoo;
- menú principal escaneable que abre o crea registros según el barcode leído;
- accesos directos por tipo de operación (`Entradas`, `Salidas`, `Internas`);
- escaneo de producto en `stock.picking`;
- escaneo de ubicación origen;
- escaneo de ubicación destino;
- escaneo de lote/serie sobre la línea actual;
- escaneo y creación de paquetes de destino;
- creación o incremento de líneas en `stock.move.line`;
- mantenimiento de un contexto de escaneo en el propio picking;
- validación guiada del flujo barcode;
- reglas clásicas por tipo de operación inspiradas en Enterprise.

No incluye todavía:

- interfaz fullscreen tipo app;
- caché reactiva;
- GS1;
- RFID;
- inventario por barcode;
- caché avanzada y orquestación frontend tipo Enterprise.

## Arquitectura del MVP

### Modelo principal

Se extiende `stock.picking` con el mixin `barcodes.barcode_events_mixin`.

Además, se añade un menú principal propio con una acción cliente mínima que escucha el servicio estándar de barcode y delega toda la resolución al backend.

Campos auxiliares:

- `xt_barcode_mode`
- `xt_barcode_current_line_id`
- `xt_barcode_source_location_id`
- `xt_barcode_destination_location_id`
- `xt_barcode_last_scan`
- `xt_barcode_last_message`

### Modos de escaneo

- `product`
- `source`
- `destination`
- `lot`
- `package`

### Menú principal

El menú principal resuelve en backend estos casos:

- picking existente;
- tipo de operación con barcode -> crea picking nuevo;
- ubicación interna -> crea picking interno;
- producto o embalaje -> abre quants internos;
- lote/serie -> abre el lote;
- paquete -> abre el paquete.

### Reglas actuales

- producto sin tracking: incrementa una línea compatible o crea una nueva;
- producto con tracking por lote: crea/incrementa línea pendiente y pasa a modo lote;
- producto con tracking por serie: crea una línea de cantidad 1 y pasa a modo lote/serie;
- ubicación origen/destino: actualiza el contexto de escaneo y, si existe, la línea actual;
- lote/serie: asigna `lot_id` o `lot_name` a la línea activa;
- paquete: selecciona o crea un `stock.package` y empaqueta la línea activa;
- el tipo de operación puede exigir origen, destino, lote/serie, paquete y bloquear productos extra;
- la validación clásica puede exigir que las líneas trabajadas queden completamente cerradas según esas reglas.

## Validación rápida

Comprobación de sintaxis:

```bash
cd /home/xtendoo/Escritorio/odoo/odoo_19_enterprise
python3 -m py_compile \
  odoo/custom/src/xtendoo/xtendoo_stock_barcode/models/stock_picking.py \
  odoo/custom/src/xtendoo/xtendoo_stock_barcode/tests/test_stock_picking_barcode.py
```

Prueba del módulo en Odoo, adaptando base de datos y servicio:

```bash
cd /home/xtendoo/Escritorio/odoo/odoo_19_enterprise
# Ejemplo orientativo; ajusta el servicio/contenedor a tu entorno
# docker compose run --rm -T odoo bash -c "odoo -d <db> --test-enable --stop-after-init -i xtendoo_stock_barcode --test-tags /xtendoo_stock_barcode"
```

