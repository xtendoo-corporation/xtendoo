from odoo import api, fields, models

import logging

class SaleOrder(models.Model):
    _inherit = "sale.order"

    pallets_number = fields.Integer(
        compute='compute_data',
        string='Pallets number',
        readonly=True,
        store=True,
    )
    lumps_number = fields.Integer(
        compute='compute_data',
        string='Lumps number',
        readonly=True,
        store=True,
    )
    has_picking = fields.Boolean(
        compute='compute_data',
        string='Has Picking',
        readonly=True,
        store=True,
    )

    def compute_data(self):
        for sale in self:
            delivery_ids = self.env['stock.picking'].search([('sale_id', '=', sale.id)])
            sale.pallets_number = sum(delivery_ids.mapped('pallets_number'))
            sale.lumps_number = sum(delivery_ids.mapped('lumps_number'))
            self.has_picking = bool(delivery_ids)



