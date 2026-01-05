# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    @api.model
    def _process_incoming_whatsapp_message(self, message_data, channel):
        """
        Procesa mensajes entrantes de WhatsApp para detectar confirmaciones pendientes.
        Este método debe ser llamado cuando se recibe un mensaje desde WhatsApp.

        :param message_data: Datos del mensaje desde la API de WhatsApp
        :param channel: Canal discuss.channel donde se recibió el mensaje
        """
        if not channel or not message_data:
            return False

        _logger.info(f"📨 Processing incoming WhatsApp message in channel {channel.name} (ID: {channel.id})")

        # Buscar confirmaciones pendientes para este canal
        pending_confirmations = self.env['whatsapp.pending.confirmation'].search([
            ('channel_id', '=', channel.id),
            ('state', '=', 'waiting')
        ])

        if not pending_confirmations:
            _logger.info(f"No pending confirmations found for channel {channel.id}")
            return False

        _logger.info(f"Found {len(pending_confirmations)} pending confirmation(s) for channel {channel.id}")

        # Procesar cada confirmación pendiente
        for pending in pending_confirmations:
            try:
                if pending.process_confirmation_response(message_data):
                    _logger.info(f"✅ Confirmation {pending.id} processed successfully")
                    # Solo procesamos una confirmación por mensaje
                    return True
            except Exception as e:
                _logger.error(f"❌ Error processing confirmation {pending.id}: {e}", exc_info=True)

        return False

    def message_post(self, **kwargs):
        """
        Override message_post to detect incoming WhatsApp messages and process confirmations.
        """
        result = super().message_post(**kwargs)

        # Si es un mensaje entrante de WhatsApp (no enviado por nosotros)
        if self.channel_type == 'whatsapp':
            # Verificar si es un mensaje entrante (no tiene author_id o author_id es el cliente)
            message_type = kwargs.get('message_type')
            author_id = kwargs.get('author_id')

            # Si no hay author_id o el author no es el usuario actual, es un mensaje entrante
            if not author_id or author_id != self.env.user.partner_id.id:
                _logger.info(f"📥 Incoming message detected in WhatsApp channel {self.name}")

                # Construir message_data básico desde kwargs
                body = kwargs.get('body', '')
                message_data = {
                    'type': 'text',
                    'text': {'body': body}
                }

                # Si el mensaje tiene algún formato especial, intentar detectarlo
                # Por ejemplo, si viene de un botón interactivo
                if hasattr(result, 'body') and result.body and any(term in result.body.lower() for term in ['button', 'interactive']):
                    message_data['type'] = 'interactive'

                # Procesar posibles confirmaciones pendientes
                try:
                    self._process_incoming_whatsapp_message(message_data, self)
                except Exception as e:
                    _logger.error(f"Error processing incoming WhatsApp message: {e}", exc_info=True)

        return result

