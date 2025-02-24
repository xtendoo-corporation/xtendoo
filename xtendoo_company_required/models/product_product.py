from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
