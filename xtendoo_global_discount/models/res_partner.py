from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    global_discount = fields.Float(
        string='Descuento global',
        help='Descuento global aplicado automáticamente en ventas y facturas',
        default=0.0
    )
