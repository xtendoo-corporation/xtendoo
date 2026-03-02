# -*- coding: utf-8 -*-

from odoo import api, fields, models


class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    feria_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente Feria',
        help='Cliente asignado permanentemente a esta mesa durante la feria. '
             'Este campo persiste independientemente de los pedidos.',
    )
    feria_partner_name = fields.Char(
        string='Nombre Cliente Feria',
        related='feria_partner_id.name',
        store=True,
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        result += ['feria_partner_id', 'feria_partner_name']
        return result


