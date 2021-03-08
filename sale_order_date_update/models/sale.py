# Copyright 2020 Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
<<<<<<< HEAD
from odoo import api, fields, models, _
=======
from odoo import _, api, fields, models
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708


class SaleOrder(models.Model):
    _inherit = "sale.order"

    date_order = fields.Datetime(
<<<<<<< HEAD
        string='Order Date',
=======
        string="Order Date",
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
        required=True,
        readonly=False,
        index=True,
        copy=False,
        default=fields.Datetime.now,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
    )
