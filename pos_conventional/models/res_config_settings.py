from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_non_touch = fields.Boolean(
        related='pos_config_id.pos_non_touch',
        readonly=False,
        string='POS no táctil',
        help='Activa un modo de punto de venta optimizado para equipos sin pantalla táctil.'
    )

