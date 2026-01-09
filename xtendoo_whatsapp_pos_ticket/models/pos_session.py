# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_pos_config(self):
        """Añadir campos de WhatsApp a la carga del POS"""
        result = super()._loader_params_pos_config()
        result['search_params']['fields'].extend([
            'whatsapp_ticket_enabled',
            'whatsapp_gateway_id',
            'whatsapp_pos_template_id',
        ])
        return result

    def _loader_params_res_partner(self):
        """Añadir campo de teléfono a la carga de partners"""
        result = super()._loader_params_res_partner()
        if 'mobile' not in result['search_params']['fields']:
            result['search_params']['fields'].append('mobile')
        if 'phone' not in result['search_params']['fields']:
            result['search_params']['fields'].append('phone')
        return result

