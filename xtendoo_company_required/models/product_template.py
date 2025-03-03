from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
