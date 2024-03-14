# Copyright 2024 Manuel Calero <http://www.xtendoo.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


READONLY_FIELD_STATES = {
    state: [('readonly', False)]
    for state in {'sale', 'done', 'cancel'}
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_order = fields.Datetime(
        string="Order Date",
        required=True,
        copy=False,
        states=READONLY_FIELD_STATES,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
        default=fields.Datetime.now,
    )
