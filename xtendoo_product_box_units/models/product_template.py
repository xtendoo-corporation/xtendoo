# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    box_units = fields.Float(
        string='Units per Box',
        digits='Product Unit of Measure',
        default=1.0,
        help='Number of units contained in one box of this product'
    )
