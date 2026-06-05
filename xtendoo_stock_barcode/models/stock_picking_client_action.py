# -*- coding: utf-8 -*-
from odoo import models, api, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_xt_get_barcode_data(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "picking_type_code": self.picking_type_id.code,
            "company_id": self.company_id.id,
            "scheduled_date": self.scheduled_date,
            "lines": [
                {
                    "id": m.id,
                    "product_id": m.product_id.id,
                    "product_name": m.product_id.display_name,
                    "product_barcode": m.product_id.barcode,
                    "qty_done": m.xt_barcode_scanned_qty,
                    "qty_demand": m.product_uom_qty,
                    "location_id": m.location_id.id,
                    "location_name": m.location_id.display_name,
                    "location_dest_id": m.location_dest_id.id,
                    "location_dest_name": m.location_dest_id.display_name,
                }
                for m in self.move_ids
                if m.state not in ('cancel', 'done')
            ],
            "locations": {
                loc.id: {"id": loc.id, "name": loc.display_name, "barcode": loc.barcode}
                for loc in (self.move_ids.location_id | self.move_ids.location_dest_id)
            },
        }

    def action_xt_process_barcode_scan(self, barcode):
        self.ensure_one()
        try:
            res = self._apply_scanned_barcode(barcode, raise_on_error=True)
            
            # Comprobar si hay exceso
            excess = False
            for m in self.move_ids:
                if m.state not in ('cancel', 'done') and m.xt_barcode_scanned_qty > m.product_uom_qty:
                    excess = True
                    break
                    
            return {"success": True, "message": "Código escaneado correctamente.", "excess": excess}
        except Exception as e:
            return {"success": False, "error": str(e)}
