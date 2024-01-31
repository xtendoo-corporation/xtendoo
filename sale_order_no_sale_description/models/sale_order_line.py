# -*- coding: utf-8 -*-

from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_id')
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if line.product_id:
                lang = line.order_id.partner_id.lang
                line.name = line.product_id.with_context(lang=lang).name or ''
