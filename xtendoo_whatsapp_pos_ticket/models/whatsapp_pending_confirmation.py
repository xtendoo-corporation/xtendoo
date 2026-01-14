# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)

class WhatsappPendingConfirmation(models.Model):
    _inherit = 'whatsapp.pending.confirmation'

    ticket_html = fields.Text(string="HTML del ticket POS")

    def process_confirmation_response(self, message_data):
        res = super().process_confirmation_response(message_data)
        # Si la confirmación es para un pedido POS y la respuesta es afirmativa, enviar el ticket
        if self.res_model == 'pos.order' and self.state == 'confirmed':
            pos_order = self.env['pos.order'].browse(self.res_id)
            ticket_html = self.ticket_html
            if not ticket_html:
                _logger.warning(f"[WhatsApp POS] No se encontró el HTML del ticket para el pedido {pos_order.name}")
            else:
                _logger.info(f"[WhatsApp POS] Enviando ticket PDF por WhatsApp tras confirmación interactiva para el pedido {pos_order.name}")
                pos_order.send_whatsapp_ticket_pdf(ticket_html)
        return res

