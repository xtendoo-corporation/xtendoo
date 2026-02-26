from odoo import models, fields


class SaleOrder(models.Model):
    """Inherit Sale Order to make date_order editable for all users"""

    _inherit = "sale.order"

    date_order = fields.Datetime(
        readonly=False,
    )
