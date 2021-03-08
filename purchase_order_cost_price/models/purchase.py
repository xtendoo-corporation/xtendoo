<<<<<<< HEAD
# -- coding: utf-8 --
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()
=======
# Copyright 2020 Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange("product_id")
    def onchange_product_id(self):
        result = super().onchange_product_id()
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
        if self.price_unit == 0.00:
            self.price_unit = self.product_id.standard_price
        return result
