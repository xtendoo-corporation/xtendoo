# POS Default Category

Este módulo permite configurar una categoría de productos por defecto para el Punto de
Venta (POS) en Odoo 19.

## Configuración

1. Ir a **Punto de Venta > Configuración > Ajustes**.
2. Seleccionar el Punto de Venta que desea configurar.
3. Buscar la sección **Productos** (Products).
4. En el campo "Categoría Inicial", seleccionar la categoría deseada.
5. Guardar los cambios.

## Funcionamiento

Al iniciar una sesión de TPV:

- El sistema verificará si hay una categoría configurada.
- Si la categoría existe, la pantalla de productos se abrirá mostrando solo los
  productos de esa categoría.
- Si no está configurada, se comportará como siempre (mostrando todos los productos).

## Detalles Técnicos

- **Modelo**: `pos.config` extendido con `default_pos_category_id`.
- **Carga de datos**: Se extiende `_load_pos_data_fields` para enviar el campo al frontend.
- **Frontend**: Se parchea `PosStore.processServerData()` para establecer
  `this.selectedCategory` con la categoría configurada.
