from odoo import api, models
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def create(self, vals):
        if not vals.get('company_id'):
            raise ValidationError("You cannot save a product without a company.")
        return super(ProductProduct, self).create(vals)

    def write(self, vals):
        if 'company_id' in vals and not vals.get('company_id'):
            raise ValidationError("You cannot save a product without a company.")
        return super(ProductProduct, self).write(vals)
