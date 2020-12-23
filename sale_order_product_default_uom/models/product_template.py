from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    uom_qty = fields.Float(
        string="Sale default units",
        default=1.00
    )

