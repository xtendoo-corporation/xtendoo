from odoo import models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _show_cancel_wizard(self):
        return False
