from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_global_discount = fields.Float(
        string='Descuento global del cliente',
        default=0.0
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_set_global_discount(self):
        if self.partner_id and self.partner_id.global_discount:
            self.customer_global_discount = self.partner_id.global_discount
        else:
            self.customer_global_discount = 0.0

    @api.onchange('customer_global_discount')
    def _onchange_customer_global_discount(self):
        for line in self.order_line:
            if line.product_id and not getattr(line.product_id, 'no_global_discount', False):
                line.discount = self.customer_global_discount
