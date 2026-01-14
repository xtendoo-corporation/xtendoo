# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    whatsapp_ticket_sent = fields.Boolean(
        string="Ticket enviado por WhatsApp",
        default=False,
        copy=False,
    )
    whatsapp_ticket_requested = fields.Boolean(
        string="Cliente ha solicitado ticket por WhatsApp",
        default=False,
        copy=False,
    )

    def _get_whatsapp_phone(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        return self.partner_id.mobile or self.partner_id.phone

    def _get_or_create_whatsapp_channel(self, gateway, phone):
        self.ensure_one()
        phone_normalized = self._normalize_phone(phone)
        channel = self.env['discuss.channel'].search([
            ('gateway_id', '=', gateway.id),
            ('gateway_channel_token', '=', phone_normalized),
        ], limit=1)
        if not channel:
            channel = self.env['discuss.channel'].create({
                'name': self.partner_id.name or phone_normalized,
                'channel_type': 'chat',
                'gateway_id': gateway.id,
                'gateway_channel_token': phone_normalized,
            })
        return channel

    @api.model
    def send_whatsapp_ticket_html(self, order_id, send_whatsapp, ticket_html):
        _logger.info("[WhatsApp POS] Iniciando envío de ticket. order_id=%s, send_whatsapp=%s", order_id, send_whatsapp)
        order = self.browse(order_id)
        if not order.exists():
            _logger.error("[WhatsApp POS] Pedido no encontrado: %s", order_id)
            return {'success': False, 'error': _('Pedido no encontrado')}
        order.ensure_one()

        if not order.partner_id:
            _logger.error("[WhatsApp POS] No hay cliente asociado al pedido: %s", order_id)
            return {'success': False, 'error': _('No hay cliente asociado al pedido')}

        phone = order._get_whatsapp_phone()
        if not phone:
            _logger.error("[WhatsApp POS] El cliente %s no tiene número de teléfono configurado", order.partner_id.name)
            return {
                'success': False,
                'error': _('El cliente %s no tiene número de teléfono configurado') % order.partner_id.name
            }

        config = order.session_id.config_id
        if not config or not config.whatsapp_gateway_id:
            _logger.error("[WhatsApp POS] No hay gateway de WhatsApp configurado en el punto de venta para el pedido %s", order.name)
            return {'success': False, 'error': _('No hay gateway de WhatsApp configurado en el punto de venta.')}

        gateway = config.whatsapp_gateway_id
        channel = order._get_or_create_whatsapp_channel(gateway, phone)
        template = config.whatsapp_pos_template_id

        if not send_whatsapp:
            # Solo enviar la plantilla configurada, sin PDF ni ticket
            if template:
                order._send_whatsapp_with_template(gateway, template, channel, None)
                _logger.info("[WhatsApp POS] Plantilla enviada correctamente por WhatsApp (sin ticket)")
                return {'success': True, 'sent': True}
            else:
                _logger.warning("[WhatsApp POS] No se encontró la plantilla configurada en POS config")
                return {'success': False, 'error': _('No se encontró la plantilla configurada en POS config')}

        try:
            _logger.info("[WhatsApp POS] Generando PDF del ticket para el pedido %s", order.name)
            pdf_content = order.env['ir.actions.report']._run_wkhtmltopdf([
                ticket_html
            ], landscape=False)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            _logger.info("[WhatsApp POS] Creando attachment PDF para el pedido %s", order.name)
            attachment = order.env['ir.attachment'].create({
                'name': 'Ticket_%s.pdf' % order.name.replace('/', '_'),
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'pos.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            })

            _logger.info("[WhatsApp POS] Enviando ticket por WhatsApp. Pedido: %s, Cliente: %s, Teléfono: %s", order.name, order.partner_id.name, phone)
            if template:
                order._send_whatsapp_with_template(gateway, template, channel, attachment)
                _logger.info("[WhatsApp POS] Ticket enviado usando plantilla de WhatsApp")
            else:
                order._send_whatsapp_simple(gateway, channel, attachment)
                _logger.info("[WhatsApp POS] Ticket enviado con mensaje simple de WhatsApp")

            order.whatsapp_ticket_sent = True
            _logger.info("[WhatsApp POS] Ticket marcado como enviado para el pedido %s", order.name)
            return {'success': True, 'sent': True}
        except Exception as e:
            _logger.exception("[WhatsApp POS] Error al enviar ticket por WhatsApp (HTML)")
            return {'success': False, 'error': str(e)}

    def _normalize_phone(self, phone):
        """Normalizar el número de teléfono para WhatsApp"""
        if not phone:
            return ''
        # Eliminar espacios, guiones y paréntesis
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        # Si empieza con +, quitar el +
        if phone.startswith('+'):
            phone = phone[1:]
        return phone

    def _send_whatsapp_with_template(self, gateway, template, channel, attachment):
        """Enviar WhatsApp usando una plantilla"""
        # Preparar variables de la plantilla
        variables = {}
        for var in template.variable_ids:
            if var.field_name:
                value = self._get_field_value(var.field_name)
                variables[var.variable_index] = str(value) if value else ''

        # Crear el mensaje en el canal con la plantilla
        message_body = template.body
        for idx, value in variables.items():
            message_body = message_body.replace('{{%s}}' % idx, value)

        # Postear mensaje con attachment
        message = channel.with_context(
            whatsapp_template_id=template.id,
            default_res_id=self.id,
            default_res_model='pos.order',
        ).message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            attachment_ids=[attachment.id] if attachment else [],
            gateway_type='whatsapp',
        )

        return message

    def _send_whatsapp_simple(self, gateway, channel, attachment):
        """Enviar WhatsApp con mensaje simple"""
        message_body = _("""🧾 *Ticket de Compra*

📅 Fecha: %s
🏪 Tienda: %s
📝 Pedido: %s

💰 *Total: %s %s*

¡Gracias por su compra!""") % (
            self.date_order.strftime('%d/%m/%Y %H:%M') if self.date_order else '',
            self.config_id.name if self.config_id else '',
            self.name or '',
            self.amount_total,
            self.currency_id.symbol if self.currency_id else '',
        )

        # Postear mensaje con attachment
        message = channel.message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            attachment_ids=[attachment.id],
            gateway_type='whatsapp',
        )

        return message

    def _get_field_value(self, field_name):
        """Obtener el valor de un campo, soportando campos relacionados con punto"""
        try:
            obj = self
            for part in field_name.split('.'):
                obj = getattr(obj, part)
            return obj
        except (AttributeError, TypeError):
            return ''

    @api.model
    def process_whatsapp_interactive_response(self, order_id, response, ticket_html=None):
        """
        Procesa la respuesta del cliente al mensaje interactivo de WhatsApp.
        Si la respuesta es 'si_ticket', envía el ticket PDF por WhatsApp.
        """
        order = self.browse(order_id)
        if not order.exists():
            _logger.error("[WhatsApp POS] Pedido no encontrado para respuesta interactiva: %s", order_id)
            return {'success': False, 'error': _('Pedido no encontrado')}
        order.ensure_one()

        if response == 'si_ticket':
            order.whatsapp_ticket_requested = True
            _logger.info("[WhatsApp POS] El cliente ha respondido SÍ, enviando ticket por WhatsApp para el pedido %s", order.name)
            # Si el HTML no se pasa, se puede regenerar o usar el último
            if not ticket_html:
                # Aquí podrías obtener el HTML desde un attachment, campo, o regenerar
                _logger.warning("[WhatsApp POS] No se proporcionó ticket_html, no se puede enviar el PDF.")
                return {'success': False, 'error': _('No se proporcionó el HTML del ticket')}
            return order.send_whatsapp_ticket_html(order.id, True, ticket_html)
        else:
            order.whatsapp_ticket_requested = False
            _logger.info("[WhatsApp POS] El cliente ha respondido NO, no se enviará el ticket por WhatsApp para el pedido %s", order.name)
            return {'success': True, 'sent': False, 'message': _('El cliente no desea recibir el ticket.')}



# NOTA: La vista pos_order_receipt_report.xml ya no es necesaria y puede eliminarse del módulo.
