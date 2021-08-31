from odoo import api, fields, models

import logging

class SaleOrder(models.Model):
    _inherit = "sale.order"

    palets_number = fields.Integer(
        compute='compute_palets_number',
        string='Pallets number',
        readonly=True,
        store=True,
    )
    lumps_number = fields.Integer(
        compute='compute_lumps_number',
        string='Lumps number',
        readonly=True,
        store=True,
    )
    has_picking = fields.Boolean(
        compute='compute_has_picking',
        string='Has Picking',
        readonly=True,
        store=True,
    )

    def compute_palets_number(self):
        for sale in self:
            delivery_ids = self.env['stock.picking'].search([('sale_id', '=', sale.id)])
            sale.palets_number = sum(delivery_ids.mapped('palets_number'))

    def compute_lumps_number(self):
        for sale in self:
            delivery_ids = self.env['stock.picking'].search([('sale_id', '=', sale.id)])
            sale.palets_number = sum(delivery_ids.mapped('lumps_number'))

    def compute_has_picking(self):
        for sale in self:
            self.has_picking = bool(self.env['stock.picking'].search([('sale_id', '=', sale.id)]))



