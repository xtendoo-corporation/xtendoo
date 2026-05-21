# Xtendoo Stock Barcode

Módulo backend-first para Odoo 19 que introduce un flujo de escaneo clásico en
`stock.picking` y una pantalla PDA propia, sin depender de `stock_barcode` ni de componentes Enterprise.

## Objetivo

Ofrecer una solución simple y mantenible basada en:

- `barcodes.barcode_events_mixin`
- `widget="barcode_handler"`
- lógica Python sobre `stock.picking`
- vistas formulario clásicas y una vista PDA propia

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
- reglas clásicas por tipo de operación;
- pantalla PDA propia para comprobar esperado vs escaneado.

No incluye todavía:

- GS1;
- RFID;
- inventario por barcode;
- caché avanzada o lógica frontend compleja.

## Arquitectura

### Modelo principal

Se extiende `stock.picking` con el mixin `barcodes.barcode_events_mixin`.

Además, se añade un menú principal propio con una acción cliente mínima que escucha el servicio estándar de barcode y delega toda la resolución al backend.

Campos auxiliares principales:

- `xt_barcode_mode`
- `xt_barcode_current_line_id`
- `xt_barcode_source_location_id`
- `xt_barcode_destination_location_id`
- `xt_barcode_last_scan`
- `xt_barcode_last_message`
- `xt_barcode_compare_state`
- `xt_barcode_expected_move_count`
- `xt_barcode_checked_move_count`
- `xt_barcode_pending_move_count`
- `xt_barcode_excess_move_count`

### Comparación PDA

La vista PDA propia abre el picking en una pantalla simplificada para comprobación y muestra:

- líneas esperadas del movimiento (`stock.move`);
- cantidad esperada vs escaneada;
- cantidad pendiente por línea;
- estado por línea: pendiente, parcial, completo o exceso;
- resumen global del picking.

### Menú principal

El menú principal resuelve en backend estos casos:

- picking existente;
- tipo de operación con barcode -> crea picking nuevo;
- ubicación interna -> crea picking interno;
- producto o embalaje -> abre quants internos;
- lote/serie -> abre el lote;
- paquete -> abre el paquete.

## Validación rápida

Comprobación de sintaxis:

```bash
cd /home/xtendoo/Escritorio/odoo/odoo_19_enterprise
python3 -m py_compile \
  odoo/custom/src/xtendoo/xtendoo_stock_barcode/models/stock_move.py \
  odoo/custom/src/xtendoo/xtendoo_stock_barcode/models/stock_picking.py \
  odoo/custom/src/xtendoo/xtendoo_stock_barcode/tests/test_stock_picking_barcode.py
```

Prueba del módulo en Odoo, adaptando base de datos y servicio:

```bash
cd /home/xtendoo/Escritorio/odoo/odoo_19_enterprise
# Ejemplo orientativo; ajusta el servicio/contenedor a tu entorno
# docker compose run --rm -T odoo bash -c "odoo -d <db> --test-enable --stop-after-init -i xtendoo_stock_barcode --test-tags /xtendoo_stock_barcode"
```
