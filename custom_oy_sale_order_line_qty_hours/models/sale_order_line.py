from odoo import api, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _convert_qty_company_hours(self, dest_company):
        return self.product_uom_qty
