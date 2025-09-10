from odoo import models, fields, api

class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    discount_in_column = fields.Float(
        string='Descuento (%) en Columna',
        digits='Discount',
        help="Descuento que se aplicará automáticamente en las líneas de venta"
    )
