# Copyright 2021 - Daniel Domínguez https://xtendoo.es/
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleInlineDiscount(models.Model):
    _name = "sale.inline.discount"
    _description = "Sale Discount inline"

    name = fields.Char()
    description = fields.Char()
    percentage = fields.Float(digits=(16, 2))
