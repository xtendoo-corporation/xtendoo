# Copyright 2017-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models

class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    standard_price = fields.Float(related="product_id.standard_price")

    total_price = fields.Float(
        compute='_compute_total_price',
        store=True,
        string='Total cost')

    @api.depends('product_id', 'product_qty', 'standard_price')
    def _compute_total_price(self):
        for res in self:
            res.total_price = res.standard_price * res.product_qty
