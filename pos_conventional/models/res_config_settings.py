from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_non_touch = fields.Boolean(
        related='pos_config_id.pos_non_touch',
        readonly=False,
        string='POS no táctil',
        help='Activa un modo de punto de venta optimizado para equipos sin pantalla táctil.'
    )

    pos_default_partner_id = fields.Many2one(
        'res.partner',
        related='pos_config_id.default_partner_id',
        readonly=False,
        string='Cliente por Defecto',
        help='Cliente que se asignará automáticamente a los nuevos pedidos POS creados desde el backend.',
        domain="[('customer_rank', '>', 0)]",
    )

