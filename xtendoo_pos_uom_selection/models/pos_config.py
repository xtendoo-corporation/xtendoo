from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    allow_uom_selection = fields.Boolean(
        string='Permitir selección de UdM',
        help='Permite a los usuarios cambiar la unidad de medición de los productos en el POS',
        default=False
    )
