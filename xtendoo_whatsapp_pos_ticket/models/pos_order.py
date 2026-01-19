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
    whatsapp_ticket_html = fields.Text(
        string="Ticket POS HTML (WhatsApp)",
        help="HTML del ticket generado en frontend para WhatsApp.",
        copy=False,
    )
    whatsapp_ticket_css = fields.Text(
        string="Ticket POS CSS (WhatsApp)",
        help="CSS del ticket generado en frontend para WhatsApp.",
        copy=False,
    )
    whatsapp_ticket_pdf = fields.Binary(
        string="Ticket POS PDF (WhatsApp)",
        help="PDF del ticket generado en frontend para WhatsApp.",
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
    def send_whatsapp_ticket_html(self, order_id, send_whatsapp, ticket_html, ticket_css=None, ticket_pdf_base64=None):
        """Recibe el HTML, CSS y PDF del ticket generado en frontend, los guarda y genera el PDF con tamaño de ticket térmico"""
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
        # Guardar el HTML y CSS recibido en el campo del pedido
        order.whatsapp_ticket_html = ticket_html or ''
        order.whatsapp_ticket_css = ticket_css or ''
        # Guardar el PDF recibido si viene desde el POS (flujo Print Full Receipt)
        if ticket_pdf_base64:
            order.whatsapp_ticket_pdf = ticket_pdf_base64
            # Asociar también a la confirmación pendiente si existe
            self.env['whatsapp.pending.confirmation'].set_ticket_pdf_for_order('pos.order', order.id, ticket_pdf_base64)
        config = order.session_id.config_id
        gateway = config.whatsapp_gateway_id
        channel = order._get_or_create_whatsapp_channel(gateway, phone)
        template = config.whatsapp_pos_template_id

        if template:
            # Enviar solo la plantilla interactiva, sin adjunto
            variables = {}
            for var in template.variable_ids:
                if var.field_name:
                    value = order._get_field_value(var.field_name)
                    variables[var.variable_index] = str(value) if value else ''
            message_body = template.body
            for idx, value in variables.items():
                message_body = message_body.replace('{{%s}}' % idx, value)
            channel.with_context(
                whatsapp_template_id=template.id,
                default_res_id=order.id,
            ).message_post(
                body=message_body,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                gateway_type='whatsapp',
            )
            if getattr(template, 'requires_confirmation', False) and template.confirmation_template_id:
                confirmation_type = template.button_ids and template.button_ids.filtered(
                    lambda b: b.button_type == 'quick_reply') and 'button' or 'any'
                order.env['whatsapp.pending.confirmation'].create({
                    'partner_id': order.partner_id.id,
                    'channel_id': channel.id,
                    'template_id': template.id,
                    'confirmation_template_id': template.confirmation_template_id.id,
                    'res_model': 'pos.order',
                    'res_id': order.id,
                    'state': 'waiting',
                    'confirmation_type': confirmation_type,
                })
            else:
                # Enviar mensaje simple sin adjunto
                message_body = _(
                    """🧾 *Ticket de Compra*\n\n📅 Fecha: %s\n🏪 Tienda: %s\n📝 Pedido: %s\n\n💰 *Total: %s %s*\n\n¡Gracias por su compra!""") % (
                                   order.date_order.strftime('%d/%m/%Y %H:%M') if order.date_order else '',
                                   order.config_id.name if order.config_id else '',
                                   order.name or '',
                                   order.amount_total,
                                   order.currency_id.symbol if order.currency_id else '',
                               )
                channel.message_post(
                    body=message_body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    gateway_type='whatsapp',
                )

            order.whatsapp_ticket_sent = True
        return {'success': True, 'sent': True}
    except Exception as e:
        _logger.exception("Error al enviar ticket por WhatsApp")
        return {'success': False, 'error': str(e)}

    def get_whatsapp_ticket_pdf(self):
        """Devuelve el PDF del ticket POS guardado en el pedido, si existe"""
        self.ensure_one()
        return self.whatsapp_ticket_pdf or False

    def generate_ticket_pdf(self):
        """Genera el PDF del ticket POS con tamaño térmico (80mm x altura automática) usando el HTML guardado y embebe el logo como base64 si es posible"""
        self.ensure_one()
        if not self.whatsapp_ticket_html:
            raise UserError(_('No hay HTML de ticket guardado en el pedido.'))
        html = self.whatsapp_ticket_html
        # Buscar el logo de la compañía y reemplazar src por base64 si es posible
        company = self.company_id or self.env.company
        if company and company.logo:
            logo_base64 = base64.b64encode(company.logo).decode('utf-8')
            logo_data_url = f"data:image/png;base64,{logo_base64}"
            import re
            html = re.sub(r'<img([^>]+)src=["\']([^"\']+logo[^"\']+)["\']',
                          fr'<img\1src="{logo_data_url}"', html, flags=re.IGNORECASE)
        # Si el HTML no tiene <style>, añadir CSS térmico por defecto
        if '<style' not in html:
            thermal_css = """
                body { background: #fff !important; color: #000 !important; }
                .pos-receipt-container { background: #fff !important; color: #000 !important; max-width: 300px; margin: 0 auto; font-size: 13px; }
                .pos-receipt-logo, .pos-company-logo { text-align: center; margin-bottom: 8px; }
                img { display: block; margin: 0 auto; }
            """
            # Insertar el CSS en el <head> si existe, si no, crear el head
            if '<head>' in html:
                html = html.replace('<head>', f'<head><style>{thermal_css}</style>')
            else:
                html = f'<html><head><style>{thermal_css}</style></head>{html}'
        pdf_content = self.env['ir.actions.report']._run_wkhtmltopdf([
            html
        ], landscape=False, specific_paperformat_args={
            'data-report-format': 'custom',
            'data-report-page-width': '80',  # mm
            'data-report-page-height': '200',  # mm, altura estimada, wkhtmltopdf ajusta si es más largo
            'data-report-margin-top': 0,
            'data-report-margin-bottom': 0,
            'data-report-margin-left': 0,
            'data-report-margin-right': 0,
        })
        return pdf_content
