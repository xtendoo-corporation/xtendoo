# Copyright 2016-2019 Akretion (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def product_price_update_before_done(self, forced_qty=None):
        super(StockMove, self).product_price_update_before_done(forced_qty)

        for move in self.filtered(
            lambda move: move.location_id.usage == "supplier"
            and move.product_id.cost_method == "last"
        ):
            supplier_info = self.env['product.supplierinfo'].search([
                    ('name', '=', move.purchase_line_id.order_id.partner_id.name),
                    ('product_tmpl_id', '=', move.product_id.product_tmpl_id.id)
                ])
            if supplier_info:
                supplier_info.sudo().write({"price": move._get_price_unit() })

            move.product_id.with_context(force_company=move.company_id.id).sudo().write(
                {"standard_price": move._get_price_unit()}
            )
