# Copyright 2020 Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super().onchange_product_id()
        if self.price_unit == 0.00:
            self.price_unit = self.product_id.standard_price
        return result
