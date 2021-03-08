# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        index=True,
        default=lambda self: self.env.user,
    )
    customer_signature = fields.Binary(
        string='Customer acceptance',
    )

    @api.model
    def create(self, values):
        picking = super().create(values)
        if picking.customer_signature:
            values = {'customer_signature': picking.customer_signature}
            picking._track_signature(values, 'customer_signature')
        return picking

    @api.multi
    def write(self, values):
        self._track_signature(values, 'customer_signature')
        return super().write(values)
