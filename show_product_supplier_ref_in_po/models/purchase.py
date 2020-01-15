# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

import logging


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    supplier_ref = fields.Char(string='Referencia proveedor')

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()

        if not self.order_id.partner_id.id:
            return result

        supplier_ref = self.env['product.supplierinfo'].search(
            [['name', '=', self.order_id.partner_id.id], ['product_tmpl_id', '=', self.product_id.id]])

        if supplier_ref != False:
            self.supplier_ref = supplier_ref.product_code

        return result
