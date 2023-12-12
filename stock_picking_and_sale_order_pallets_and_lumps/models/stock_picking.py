# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPickingBatch(models.Model):
    _inherit = ["stock.picking"]

    lumps_number = fields.Integer(
        string="Lumps",
        store=True,
    )
    palets_number = fields.Integer(
        string="Palets",
        store=True,
    )
