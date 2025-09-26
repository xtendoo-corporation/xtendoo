# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    lumps_number = fields.Integer(
        string="Lumps",
        store=True,
        default=0,
        copy=False,
    )
    pallets_number = fields.Integer(
        string="Pallets",
        store=True,
        default=0,
        copy=False,
    )
