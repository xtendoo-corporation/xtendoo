from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    no_global_discount = fields.Boolean(
        string='Sin descuento global',
        help='Si está marcado, este producto no tendrá descuento global automático'
    )
