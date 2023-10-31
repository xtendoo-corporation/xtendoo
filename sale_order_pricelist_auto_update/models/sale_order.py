# Copyright 2021 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"


    def _action_confirm(self):
        result = ""
        for line in self.order_line:
            if line.compute_price_unit_is_valid():
                result += line.compute_price_unit_is_valid()
        if result:
            raise UserError(result)
        return super(SaleOrder, self)._action_confirm()


