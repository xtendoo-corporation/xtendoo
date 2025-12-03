from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.onchange('product_id', 'qty', 'price_unit', 'discount', 'tax_ids_after_fiscal_position')
    def _onchange_amount(self):
        """Recalcula los subtotales cuando se modifican los campos de la línea"""
        if self.order_id.state == 'draft':
            # Calcular el precio con descuento
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)

            # Obtener los impuestos
            taxes = self.tax_ids_after_fiscal_position
            if taxes:
                # Calcular impuestos
                taxes_result = taxes.compute_all(
                    price,
                    currency=self.order_id.currency_id,
                    quantity=self.qty,
                    product=self.product_id,
                    partner=self.order_id.partner_id
                )
                self.price_subtotal = taxes_result['total_excluded']
                self.price_subtotal_incl = taxes_result['total_included']
            else:
                # Sin impuestos
                self.price_subtotal = price * self.qty
                self.price_subtotal_incl = self.price_subtotal

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Establece el precio unitario cuando se selecciona un producto"""
        if self.product_id and self.order_id.state == 'draft':
            # Verificar que el pedido tenga la configuración básica
            if not self.order_id.pricelist_id:
                self.price_unit = self.product_id.lst_price
            else:
                # Obtener el precio del producto usando la API correcta de Odoo 19
                pricelist = self.order_id.pricelist_id
                price = pricelist._get_product_price(
                    self.product_id,
                    self.qty or 1.0,
                    uom=self.product_id.uom_id
                )
                self.price_unit = price

            # Establecer los impuestos
            if self.order_id.fiscal_position_id:
                self.tax_ids = self.order_id.fiscal_position_id.map_tax(
                    self.product_id.taxes_id.filtered(
                        lambda t: t.company_id == self.order_id.company_id
                    )
                )
            else:
                self.tax_ids = self.product_id.taxes_id.filtered(
                    lambda t: t.company_id == self.order_id.company_id
                )

