# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

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

