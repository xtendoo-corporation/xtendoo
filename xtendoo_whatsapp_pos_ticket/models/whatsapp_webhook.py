# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)

class WhatsappPendingConfirmationPos(models.Model):
    _inherit = 'whatsapp.pending.confirmation'

    def process_confirmation_response(self, message_data, ticket_html=None):
        """
        Extiende el procesamiento de la respuesta para POS: si es POS y confirmado, envía el PDF usando el HTML guardado.
        """
        self.ensure_one()
        result = super().process_confirmation_response(message_data)
        if result and self.state == 'confirmed' and self.res_model == 'pos.order':
            order = self.env['pos.order'].browse(self.res_id)
            html = self.ticket_html or ticket_html
            if order.exists() and html:
                _logger.info(f"[WhatsApp POS] Enviando PDF tras confirmación para pedido {order.name}")
                order.send_whatsapp_ticket_pdf(html)
        return result
