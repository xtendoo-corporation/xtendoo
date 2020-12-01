from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    _sql_constraints = [
        ('name_ref_uniq', 'unique (id, name, product_id, company_id)', 'The combination of serial number and product must be unique across a company !'),
    ]
