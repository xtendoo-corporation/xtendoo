from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_qty = fields.Float(
        string="Secondary Qty",
        digits="Product Unit of Measure",
    )

