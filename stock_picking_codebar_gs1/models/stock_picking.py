# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = ["barcodes.barcode_events_mixin", "stock.picking"]
    _name = "stock.picking"

    barcode = fields.Char(store=False)
    packaging_id = fields.Many2one(comodel_name="product.packaging", store=False)
    product_id = fields.Many2one(comodel_name="product.product", store=False,)
    lot_id = fields.Many2one(comodel_name="stock.production.lot", store=False,)
    product_qty = fields.Float(
        digits=dp.get_precision("Product Unit of Measure"), store=False,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking", string="Picking", readonly=True, store=False,
    )

    def action_barcode_scan(self):
        out_picking = self.picking_type_code == 'outgoing'
        location = self.location_id if out_picking else self.location_dest_id
        action = self.env.ref(
            'stock_barcodes.action_stock_barcodes_read_picking').read()[0]
        action['context'] = {
            'default_location_id': location.id,
            'default_partner_id': self.partner_id.id,
            'default_picking_id': self.id,
            'default_res_model_id':
                self.env.ref('stock.model_stock_picking').id,
            'default_res_id': self.id,
            'default_picking_type_code': self.picking_type_code,
        }
        return action

    def _barcode_domain(self, barcode):
        return [("barcode", "=", barcode)]

    def _lot_domain(self, lot_barcode):
        return [
            ("name", "=", lot_barcode),
            ("product_id", "=", self.product_id.id),
        ]

    def action_product_scaned_post(self, product):
        self.packaging_id = False
        if self.product_id != product:
            self.lot_id = False
        self.product_id = product

        print("producto asignado product", product)
        print("producto asignado self.product_id", self.product_id)

        self.product_qty = 1.0

    def action_lot_scaned_post(self, lot):
        self.lot_id = lot

    @api.onchange("move_line_ids_without_package")
    def onchange_move_ids_without_package(self):
        print("move_line_ids_without_packageeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")

    def on_barcode_scanned(self, barcode):
        self.barcode = barcode
        self.picking_id = self._origin
        if self.process_barcode():
            self._process_stock_move_line()
        return {"type": "ir.actions.client", "tag": "reload"}

    def process_barcode(self):
        """ Only has been implemented AI (01, 02, 10, 37), so is possible that
        scanner reads a barcode ok but this one is not precessed.
        """
        try:
            barcode_decoded = self.env["gs1_barcode"].decode(self.barcode)
        except Exception:
            self.env.user.notify_danger(message=_("Barcode error formated!"))
            return False
        processed = False
        package_barcode = barcode_decoded.get("01", False)
        product_barcode = barcode_decoded.get("02", False)
        if not product_barcode:
            # Sometimes the product does not yet have a GTIN. In this case
            # try the AI 240 'Additional product identification assigned
            # by the manufacturer'.
            product_barcode = barcode_decoded.get("240", False)
        lot_barcode = barcode_decoded.get("10", False)
        product_qty = barcode_decoded.get("37", 1)
        if product_barcode:
            product = self.env["product.product"].search(
                self._barcode_domain(product_barcode)
            )
            if not product:
                self.env.user.notify_danger(message=_("Barcode for product not found"))
                return False
            else:
                processed = True
                self.action_product_scaned_post(product)
        if package_barcode:
            packaging = self.env["product.packaging"].search(
                self._barcode_domain(package_barcode)
            )
            if not packaging:
                self.env.user.notify_danger(
                    message=_("Barcode for product packaging not found")
                )
                return False
            if len(packaging) > 1:
                self.env.user.notify_danger(message=_("More than one package found"))
                return False
            processed = True
            self.action_packaging_scaned_post(packaging)
        if lot_barcode and self.product_id.tracking != "none":
            lot = self.env["stock.production.lot"].search(self._lot_domain(lot_barcode))
            if not lot:
                self.env.user.notify_danger(message=_("Lot for product not found"))
                return False
            processed = True
            self.action_lot_scaned_post(lot)
        if product_qty:
            self.product_qty = product_qty
        if processed:
            print("Barcode read correctly")
            self.env.user.notify_info(message=_("Barcode read correctly"))
            return True
        self.env.user.notify_danger(message=_("Barcode not found"))
        return False

    def _stock_moves_domain(self):
        domain = [
            ("picking_id", "=", self.picking_id.id),
            ("product_id", "=", self.product_id.id),
            ("picking_id.picking_type_id.code", "=", self.picking_type_code),
            ("state", "in", ["assigned", "confirmed"]),
        ]
        return domain

    def _process_stock_move_line(self):
        """
        Search assigned or confirmed stock moves from a picking operation type
        or a picking. If there is more than one picking with demand from
        scanned product the interface allow to select what picking to work.
        If only there is one picking the scan data is assigned to it.
        """
        if not self.product_qty:
            self.env.user.notify_danger(message=_("Waiting quantities"))
            return
        if self.product_id.tracking != "none" and not self.lot_id:
            self.env.user.notify_danger(message=_("Waiting for input lot"))
            return
        stock_moves = self.env["stock.move"].search(self._stock_moves_domain())
        if not stock_moves:
            self.env.user.notify_danger(
                message=_("There are no stock moves to assign this operation")
            )
            return

        print("stock_moves >>>>>>>>>> ", stock_moves)

        available_qty = self.product_qty

        lines = stock_moves.mapped("move_line_ids").filtered(
            lambda l: (l.lot_id == self.lot_id)
        )
        for line in lines:
            print("line==========================", line)
            if line.product_uom_qty:
                assigned_qty = min(
                    max(line.product_uom_qty - line.qty_done, 0.0), available_qty
                )
            else:
                assigned_qty = available_qty
            line.write({"qty_done": line.qty_done + assigned_qty})
            available_qty -= assigned_qty
            if (
                float_compare(
                    available_qty,
                    0.0,
                    precision_rounding=line.product_id.uom_id.rounding,
                )
                < 1
            ):
                break
        if (
            float_compare(
                available_qty, 0, precision_rounding=self.product_id.uom_id.rounding
            )
            > 0
        ):
            # Create an extra stock move line if this product has an
            # initial demand.

            print("self.picking_id.move_lines >>>>>>>>>>", self.picking_id.move_lines)

            self.env["stock.move.line"].create(
                self._prepare_move_line_values(stock_moves[0], available_qty)
            )

    def _prepare_move_line_values(self, stock_move, available_qty):
        """When we've got an out picking, the logical workflow is that
           the scanned location is the location we're getting the stock
           from"""
        out_move = stock_move.picking_code == "outgoing"
        location_id = self.location_id if out_move else self.picking_id.location_id
        location_dest_id = (
            self.picking_id.location_dest_id if out_move else self.location_id
        )
        return {
            "picking_id": self.picking_id.id,
            "move_id": stock_move.id,
            "qty_done": available_qty,
            "product_uom_id": self.product_id.uom_po_id.id,
            "product_id": self.product_id.id,
            "location_id": location_id.id,
            "location_dest_id": location_dest_id.id,
            "lot_id": self.lot_id.id,
            "lot_name": self.lot_id.name,
        }
