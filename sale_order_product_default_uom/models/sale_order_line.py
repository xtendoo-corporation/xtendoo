<<<<<<< HEAD
from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
=======
from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("product_id")
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
    def _onchange_product_id(self):
        if not self.product_id:
            return
        if self.product_id.product_tmpl_id.uom_qty != 0:
            self.product_uom_qty = self.product_id.product_tmpl_id.uom_qty
<<<<<<< HEAD

=======
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
