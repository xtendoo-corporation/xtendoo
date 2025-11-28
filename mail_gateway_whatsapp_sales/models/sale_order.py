# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_send_whatsapp(self):
        """Abre el wizard para enviar WhatsApp desde el pedido."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.whatsapp.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            },
        }

