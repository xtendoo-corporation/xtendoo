# Copyright Copyright 2021 Daniel Dominguez, Manuel Calero - https://xtendoo.es
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_view_scan_picking(self):
        picking = self.mapped("picking_ids").sorted("id")[:1]
        return {
            'type': 'ir.actions.act_multi',
            'actions': [
                self.action_view_picking(),
                picking.action_barcode_scan()
            ]
        }


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["barcodes.barcode_events_mixin", "stock.picking"]

    barcode = fields.Char()

    def action_init(self):
        print("*** action init ***")

    @api.model
    def create(self, vals):
        print("*** create ***")
        return super().create(vals)

    def write(self, vals):
        print("*** write ***")
        return super().write(vals)

    @api.model
    def default_get(self, default_fields):
        print("*** default_get ***")
        return super().default_get(default_fields)

    def on_barcode_scanned(self, barcode):
        print("on_barcode_scanned read:::::", barcode)
