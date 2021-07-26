# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging


class StockPickingBatch(models.Model):
    _inherit = ["stock.picking"]

    lumps_number = fields.Integer(
        string="Lumps",
        store=True,
    )
    pallets_number = fields.Integer(
        string="Pallets",
        store=True,
    )
