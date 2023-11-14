from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class ProductionLot(models.Model):
    _inherit = "stock.production.lot"

    @api.constrains('name', 'product_id', 'company_id')
    def _check_unique_lot(self):
        return
