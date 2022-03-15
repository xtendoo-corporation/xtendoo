from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('partner_id')
    def onchange_inline_discount(self):
        for line in self.order_line:
            line.sale_inline_discount_ids = self.partner_id.sale_inline_discount_ids
            line.onchange_sale_inline_discount_ids()

