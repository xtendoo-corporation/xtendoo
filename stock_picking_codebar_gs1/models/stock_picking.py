# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = ['barcodes.barcode_events_mixin', 'stock.picking']
    _name = 'stock.picking'


    def on_barcode_scanned(self, barcode):
        try:
            barcode_decoded = self.env['gs1_barcode'].decode(barcode)
        except Exception:
            return       
        print("on_barcode_scanned*****************", barcode_decoded)
