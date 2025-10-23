from odoo import models, fields

class ProductTag(models.Model):
    _inherit = 'product.tag'

    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True, index=True)


