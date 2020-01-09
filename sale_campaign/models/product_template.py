from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    promotion_ids = fields.Many2many(
        comodel_name='sale.promotion',
        string='Promotions')
