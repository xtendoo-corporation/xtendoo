from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_product_id(self):
        # Esta es la versión correcta del método en Odoo 18
        result = super()._onchange_product_id()

        if self.product_id and self.order_id.pricelist_id:
            # Buscamos si existe un descuento en la tarifa para este producto
            pricelist_items = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', self.order_id.pricelist_id.id),
                '|', '|', '|',
                # Caso 1: Variante de producto específica
                '&',
                ('product_id', '=', self.product_id.id),
                ('applied_on', '=', '0_product_variant'),
                # Caso 2: Plantilla de producto
                '&',
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                ('applied_on', '=', '1_product'),
                # Caso 3: Categoría de producto
                '&',
                ('categ_id', '=', self.product_id.categ_id.id),
                ('applied_on', '=', '2_product_category'),
                # Caso 4: Global (todos los productos)
                ('applied_on', '=', '3_global'),
            ], order='applied_on, min_quantity desc', limit=1)

            # Si encontramos un item con descuento, lo aplicamos
            if pricelist_items and pricelist_items.discount_in_column:
                self.discount = pricelist_items.discount_in_column

        return result
