from odoo import models


class SaleOrder(models.Model):
    """Inherit Sale Order to make date_order editable for all users"""

    _inherit = "sale.order"
