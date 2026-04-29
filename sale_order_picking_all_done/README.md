# Sale Order Picking All Done

Automatiza acciones habituales del pedido de venta:

- confirmar y entregar todos los albaranes pendientes,
- entregar pedidos ya confirmados,
- entregar, crear factura y publicarla automáticamente.

La entrega usa la cantidad pedida en cada movimiento de stock. Si la línea de
venta tiene un lote seleccionado mediante `sale_order_lot_selection`, el módulo
respeta el lote propagado al movimiento (`restrict_lot_id`) y lo aplica en las
líneas del albarán antes de validar.

El módulo no modifica políticas de facturación de productos ni campos
computados de Odoo como `qty_delivered` o `qty_to_invoice`; deja que el flujo
estándar de entrega actualice esas cantidades y después crea la factura con
`sale.order._create_invoices()`.
