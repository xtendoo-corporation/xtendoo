from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pallets_number = fields.Integer(
        compute='_compute_pallets_number',
        string='Pallets number',
    )
    lumps_number = fields.Integer(
        compute='_compute_lumps_number',
        string='Lumps number',
    )
    has_picking = fields.Boolean(
        compute='_compute_has_picking',
        string='Has picking',
    )

    def _compute_pallets_number(self):
        self.pallets_number = sum(self.picking_ids.mapped("pallets_number")) or 0.0

    def _compute_lumps_number(self):
        self.lumps_number = sum(self.picking_ids.mapped("lumps_number")) or 0.0

    def _compute_has_picking(self):
        self.has_picking = len(self.picking_ids) > 0
