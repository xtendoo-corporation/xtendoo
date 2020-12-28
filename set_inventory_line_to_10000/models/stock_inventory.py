# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Inventory(models.Model):
    _name = "stock.inventory"
    _inherit = ["stock.inventory"]

    def action_set_product_qty_to_10000(self):
        self.mapped("line_ids").write({"product_qty": 10000})
        # self.mapped("line_ids").write({"theoretical_qty": 10000})
        return True
