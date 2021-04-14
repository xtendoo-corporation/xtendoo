from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = ["product.template", "administrator.mixin.rule"]
    _name = 'product.template'