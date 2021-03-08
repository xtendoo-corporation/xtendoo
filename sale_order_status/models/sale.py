# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2020 Xtendoo - Manuel Calero Solís

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    status_id = fields.Many2one(
        comodel_name="sale.order.status", string="Status", store=True, readonly=False,
    )
