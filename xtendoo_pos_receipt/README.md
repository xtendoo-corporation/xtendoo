# xtendoo_pos_receipt

Recibo del TPV personalizado de Xtendoo (cabecera con datos de empresa y cliente,
líneas Nombre / UD / TOTAL, TOTAL, forma de pago, tabla de impuestos y pie).

## Odoo 20

El recibo de Odoo 20 se genera con plantillas QWeb (`point_of_sale.pos_order_receipt`)
compartidas por backend y frontend, así que el módulo solo hereda esas plantillas
(`receipt/pos_order_receipt.xml`). Se eliminaron el JS/OWL y el modelo Python de la 19.

Ya no depende de `l10n_es_pos` (marcado como obsoleto en Odoo 20).
