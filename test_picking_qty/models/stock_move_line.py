# Copyright 2021 Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Este metodo rellena la referecias a la linea del pedido de la que proviene
# es para corregir un error de Odoo que en los pickings con rutas

from odoo import _, models, api


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    @api.onchange('qty_done')
    def _onchange_qty_done(self):
        res = super()._onchange_qty_done()
        print("*" * 80)
        print("ENTRA qty on change")
        print("*" * 80)
        if self.qty_done > self.product_uom_qty:
            self.product_uom_qty = self.qty_done
        return res

