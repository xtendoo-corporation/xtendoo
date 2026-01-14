# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
import logging
_logger = logging.getLogger(__name__)

class WhatsappPendingConfirmation(models.Model):
    _inherit = 'whatsapp.pending.confirmation'

    def process_confirmation_response(self, message_data):
        res = super().process_confirmation_response(message_data)
        # Si la confirmación es para un pedido POS y la respuesta es 'si_ticket', enviar el ticket
        if self.res_model == 'pos.order' and self.state == 'confirmed':
            # Buscar el pedido POS
            pos_order = self.env['pos.order'].browse(self.res_id)
            if pos_order.exists():
                # Obtener el HTML del ticket (puedes guardar el HTML en un campo, attachment, o generarlo)
                ticket_html = getattr(pos_order, 'last_ticket_html', None)
                if not ticket_html:
                    _logger.warning(f"[WhatsApp POS] No se encontró el HTML del ticket para el pedido {pos_order.name}")
                else:
                    _logger.info(f"[WhatsApp POS] Enviando ticket PDF por WhatsApp tras confirmación interactiva para el pedido {pos_order.name}")
                    pos_order.send_whatsapp_ticket_html(pos_order.id, True, ticket_html)
        return res

