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

    def _get_whatsapp_phone(self):
        """Obtener el número de teléfono del cliente para WhatsApp"""
        self.ensure_one()
        if not self.partner_id:
            return False
        return self.partner_id.mobile or self.partner_id.phone

    def action_send_whatsapp_ticket(self):
        """Enviar el ticket por WhatsApp al cliente"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("No hay cliente asociado a este pedido."))

        phone = self._get_whatsapp_phone()
        if not phone:
            raise UserError(_("El cliente %s no tiene número de teléfono configurado.") % self.partner_id.name)

        # Obtener configuración
        config = self.session_id.config_id
        if not config.whatsapp_gateway_id:
            raise UserError(_("No hay gateway de WhatsApp configurado en el punto de venta."))

        gateway = config.whatsapp_gateway_id
        template = config.whatsapp_pos_template_id

        # Generar el PDF del ticket
        report = self.env.ref('point_of_sale.pos_order_report')
        pdf_content, content_type = report._render_qweb_pdf(report.id, [self.id])
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        # Crear el attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Ticket_%s.pdf' % self.name.replace('/', '_'),
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': 'pos.order',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        # Buscar o crear el canal de WhatsApp para este cliente
        channel = self._get_or_create_whatsapp_channel(gateway, phone)

        if template:
            # Usar la plantilla configurada
            self._send_whatsapp_with_template(gateway, template, channel, attachment)
        else:
            # Enviar mensaje simple con el PDF
            self._send_whatsapp_simple(gateway, channel, attachment)

        self.whatsapp_ticket_sent = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('WhatsApp'),
                'message': _('Ticket enviado correctamente por WhatsApp'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_or_create_whatsapp_channel(self, gateway, phone):
        """Buscar o crear el canal de WhatsApp para el cliente"""
        # Normalizar el número de teléfono
        phone_normalized = self._normalize_phone(phone)

        # Buscar canal existente
        channel = self.env['discuss.channel'].search([
            ('gateway_id', '=', gateway.id),
            ('gateway_channel_token', '=', phone_normalized),
        ], limit=1)

        if not channel:
            # Crear nuevo canal
            channel = self.env['discuss.channel'].create({
                'name': self.partner_id.name or phone_normalized,
                'channel_type': 'chat',
                'gateway_id': gateway.id,
                'gateway_channel_token': phone_normalized,
            })

        return channel

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
            attachment_ids=[attachment.id],
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
    def send_whatsapp_ticket_from_ui(self, order_id, send_whatsapp):
        """Método llamado desde el frontend del POS"""
        if not send_whatsapp:
            return {'success': True, 'sent': False}

        order = self.browse(order_id)
        if not order.exists():
            return {'success': False, 'error': _('Pedido no encontrado')}

        if not order.partner_id:
            return {'success': False, 'error': _('No hay cliente asociado al pedido')}

        phone = order._get_whatsapp_phone()
        if not phone:
            return {
                'success': False,
                'error': _('El cliente %s no tiene número de teléfono configurado') % order.partner_id.name
            }

        try:
            order.action_send_whatsapp_ticket()
            return {'success': True, 'sent': True}
        except Exception as e:
            _logger.exception("Error al enviar ticket por WhatsApp")
            return {'success': False, 'error': str(e)}

    @api.model
    def send_whatsapp_ticket_html(self, order_id, send_whatsapp, ticket_html):
        """Recibe el HTML del ticket generado en frontend, lo convierte a PDF y lo envía por WhatsApp"""
        if not send_whatsapp:
            return {'success': True, 'sent': False}

        order = self.browse(order_id)
        if not order.exists():
            return {'success': False, 'error': _('Pedido no encontrado')}

        if not order.partner_id:
            return {'success': False, 'error': _('No hay cliente asociado al pedido')}

        phone = order._get_whatsapp_phone()
        if not phone:
            return {
                'success': False,
                'error': _('El cliente %s no tiene número de teléfono configurado') % order.partner_id.name
            }

        try:
            # Convertir el HTML a PDF usando el motor de reportes de Odoo
            pdf_content = order.env['ir.actions.report']._run_wkhtmltopdf([
                ticket_html
            ], landscape=False)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            # Crear el attachment
            attachment = order.env['ir.attachment'].create({
                'name': 'Ticket_%s.pdf' % order.name.replace('/', '_'),
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'pos.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            })

            # Buscar o crear el canal de WhatsApp para este cliente
            config = order.session_id.config_id
            gateway = config.whatsapp_gateway_id
            channel = order._get_or_create_whatsapp_channel(gateway, phone)
            template = config.whatsapp_pos_template_id

            if template:
                order._send_whatsapp_with_template(gateway, template, channel, attachment)
            else:
                order._send_whatsapp_simple(gateway, channel, attachment)

            order.whatsapp_ticket_sent = True
            return {'success': True, 'sent': True}
        except Exception as e:
            _logger.exception("Error al enviar ticket por WhatsApp (HTML)")
            return {'success': False, 'error': str(e)}
