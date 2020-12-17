from odoo import api, fields, models

import logging

class SaleOrder(models.Model):
    _inherit = "sale.order"

    palets_number = fields.Integer(compute='compute_palets_number', string='Pallets number')

    lumps_number = fields.Integer(compute='compute_lumps_number', string='Lumps number')

    has_picking = fields.Boolean(compute='compute_has_picking', string='Has Picking')

    def compute_palets_number(self):
        palets_number=0
        delivery_ids = self.env['stock.picking'].search([('sale_id', '=', self.id)])
        for delivery_id in delivery_ids:
            palets_number+=delivery_id.palets_number
        self.palets_number=palets_number

    def compute_lumps_number(self):
        lumps_number=0
        delivery_ids = self.env['stock.picking'].search([('sale_id', '=', self.id)])
        for delivery_id in delivery_ids:
            lumps_number+=delivery_id.lumps_number
        self.lumps_number=lumps_number

    def compute_has_picking(self):
        delivery_ids=self.env['stock.picking'].search([('sale_id', '=', self.id)])
        has_picking=False
        if delivery_ids:
            has_picking=True
        self.has_picking=has_picking



