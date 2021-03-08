# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderStatus(models.Model):
    _name = "sale.order.status"
    _description = "Status of sale order"

    name = fields.Char(required=True, translate=True)
