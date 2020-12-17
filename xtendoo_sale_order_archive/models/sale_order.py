# Copyright 2020 Manuel Calero - (<https://xtendoo.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(default=True)

