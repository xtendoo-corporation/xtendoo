# Copyright 2021 Manuel Calero Solís (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_conditional_weight = fields.Float(
        compute='_compute_total_conditional_weight',
        string='Total Weight',
        store=True
    )

    @api.depends('state')
    def _compute_total_conditional_weight(self):
        for order in self:
            if order.total_delivered_weight != 0.0:
                order.total_conditional_weight = order.total_delivered_weight
            else:
                order.total_conditional_weight = order.total_ordered_weight
