# Copyright 2020 Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        readonly=False,
        index=True,
        copy=False,
        default=fields.Datetime.now,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
    )
