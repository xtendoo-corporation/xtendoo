# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import _

class StockBarcodeInternalWizard(models.TransientModel):
    _name = 'stock.barcode.internal.wizard'
    _description = 'Wizard para transferencias internas por almacén'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
    )

    def action_continue(self):
        self.ensure_one()
        # Buscamos la ubicación de stock del almacén seleccionado
        location = self.warehouse_id.lot_stock_id

        # Devolvemos la acción del cliente de barcode pero con un parámetro especial para indicar que es por ubicación
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_stock_barcode_client_action",
            "name": _("Transferencias internas: %s") % self.warehouse_id.name,
            "target": "fullscreen",
            "params": {
                "model": "stock.picking",
                "location_id": location.id,
                "warehouse_id": self.warehouse_id.id,
                "mode": "aggregated",
            }
        }
