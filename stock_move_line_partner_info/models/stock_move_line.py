# Copyright 2024 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    partner_id = fields.Many2one(
        string='Partner',
        related='move_id.partner_id',
        store=True,
    )
