# Copyright 2020 Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        print("pasaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        return res
