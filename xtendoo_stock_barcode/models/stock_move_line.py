# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    xt_barcode_product_scanned = fields.Boolean(
        string="Producto confirmado por barcode",
        copy=False,
    )
    xt_barcode_source_scanned = fields.Boolean(
        string="Origen confirmado por barcode",
        copy=False,
    )
    xt_barcode_destination_scanned = fields.Boolean(
        string="Destino confirmado por barcode",
        copy=False,
    )
    xt_barcode_tracking_scanned = fields.Boolean(
        string="Lote/serie confirmado por barcode",
        copy=False,
    )
    xt_barcode_package_scanned = fields.Boolean(
        string="Paquete confirmado por barcode",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("picking_id"):
                picking = self.env["stock.picking"].browse(vals["picking_id"])
                if not vals.get("result_package_id") and picking.xt_barcode_current_package_id:
                    vals["result_package_id"] = picking.xt_barcode_current_package_id.id
                if not vals.get("location_dest_id") and picking.xt_barcode_destination_location_id:
                    vals["location_dest_id"] = picking.xt_barcode_destination_location_id.id
        return super().create(vals_list)

