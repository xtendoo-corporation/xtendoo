# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import logging


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def button_mark_done(self):
        #Funcionalidad de cambiar el coste por la suma de los costes
        coste_total = 0
        pvp_total = 0

        for line in self.move_raw_ids:
            #Calculamos el nuevo precio de coste y el pvp
            coste = line.product_id.standard_price * line.product_qty
            pvp = line.product_id.list_price * line.product_qty

            #Acumulamos el importe
            coste_total = coste_total + coste
            pvp_total = pvp_total + pvp

        #Actualizamos el precio de coste y venta
        self.product_id.standard_price = coste_total
        #self.product_id.list_price = pvp_total

        return super().button_mark_done()
