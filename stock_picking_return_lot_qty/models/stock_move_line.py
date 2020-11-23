# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    partner_id = fields.Many2one(
        related='picking_id.partner_id',
        string='Partner',
        readonly=True,
    )
    sale_id = fields.Many2one(
        related='picking_id.sale_id',
        string="Sales Order",
        readonly=True
    )
    invoice_status = fields.Selection(
        related='picking_id.sale_id.invoice_status',
        string='Invoice Status',
        readonly=True,
    )
