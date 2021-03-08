from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        if self.product_id.product_tmpl_id.uom_qty != 0:
            self.product_uom_qty = self.product_id.product_tmpl_id.uom_qty

