# Copyright 2021 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"


    def _action_confirm(self):
        for line in self.order_line:
            line._onchange_price_unit()
        return super(SaleOrder, self)._action_confirm()


