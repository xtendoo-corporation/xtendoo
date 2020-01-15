# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = ['stock.picking.batch']

    delivery_id = fields.Many2one('delivery.carrier', string='Método de entrega')

    date_planned = fields.Datetime(
        'Fecha', default=fields.Datetime.now, index=True, required=True,
        states={'done': [('readonly', True)]})