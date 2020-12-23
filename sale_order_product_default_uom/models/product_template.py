from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_qty = fields.Float(
        string="Sale default units",
        digits="Product Unit of Measure",
    )

