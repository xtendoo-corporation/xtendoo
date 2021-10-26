# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _name = "stock.picking"

    def action_barcode_scan(self):
        out_picking = self.picking_type_code == "outgoing"
        location = self.location_id if out_picking else self.location_dest_id
        action = self.env.ref(
            "xtendoo_stock_picking_barcodes.action_stock_barcodes_read_picking"
        ).read()[0]
        action["context"] = {
            "default_location_id": location.id,
            "default_partner_id": self.partner_id.id,
            "default_picking_id": self.id,
            "default_res_model_id": self.env.ref("stock.model_stock_picking").id,
            "default_res_id": self.id,
            "default_picking_type_code": self.picking_type_code,
        }
        return action


class TrnLinePicking(models.TransientModel):
    _name = "trn.line.picking"
    _description = "Line pickings for barcode interface"
    _transient_max_hours = 48

    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Picking", readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", required=True,
    )
    reserved_availability = fields.Float(
        string="Reserved", digits="Product Unit of Measure", readonly=True,
    )
    product_uom_qty = fields.Float(
        string="Demand", digits="Product Unit of Measure", readonly=True,
    )
    quantity_done = fields.Float(
        string="Done", digits="Product Unit of Measure", readonly=True,
    )
    # For reload kanban view
    scan_count = fields.Integer()

    @api.depends("scan_count")
    def _compute_picking_quantity(self):
        for candidate in self:
            qty_reserved = 0
            qty_demand = 0
            qty_done = 0
            candidate.product_qty_reserved = sum(
                candidate.picking_id.mapped("move_lines.reserved_availability")
            )
            for move in candidate.picking_id.move_lines:
                qty_reserved += move.reserved_availability
                qty_demand += move.product_uom_qty
                qty_done += move.quantity_done
            candidate.update(
                {
                    "product_qty_reserved": qty_reserved,
                    "product_uom_qty": qty_demand,
                    "product_qty_done": qty_done,
                }
            )

    def _get_wizard_barcode_read(self):
        return self.env["wiz.stock.barcodes.read.picking"].browse(
            self.env.context["wiz_barcode_id"]
        )
