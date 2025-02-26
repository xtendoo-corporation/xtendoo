from collections import defaultdict
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    def product_price_update_before_done(self, forced_qty=None):
        super().product_price_update_before_done(forced_qty=forced_qty)
        for move in self.filtered(lambda m: m.with_company(m.company_id).product_id.cost_method == 'last' and
                                            m.product_id.valuation in ['real_time', 'manual_periodic']):
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {'standard_price': move._get_price_unit()})
