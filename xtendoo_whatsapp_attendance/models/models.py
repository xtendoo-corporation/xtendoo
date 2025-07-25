from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class AttendanceKeywordConfig(models.Model):
    _name = 'attendance.keyword.config'
    _description = 'Configuración de Palabras Clave para Asistencia WhatsApp'
    _rec_name = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre descriptivo para esta configuración'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está activo, estas palabras clave serán utilizadas'
    )

    attendance_type = fields.Selection([
        ('check_in', 'Entrada'),
        ('check_out', 'Salida')
    ], string='Tipo de Asistencia', required=True)

    keywords = fields.Text(
        string='Palabras Clave',
        required=True,
        help='Una palabra clave por línea. Se pueden usar expresiones regulares básicas.'
    )

    whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='Plantilla WhatsApp',
        help='Plantilla aprobada de WhatsApp para enviar confirmación'
    )

    custom_message = fields.Text(
        string='Mensaje Personalizado',
        help='Mensaje personalizado si no se usa plantilla. Variables: {employee_name}, {time}, {date}, {action}'
    )

    use_template = fields.Boolean(
        string='Usar Plantilla WhatsApp',
        default=False,
        help='Si está marcado, usará la plantilla de WhatsApp, sino el mensaje personalizado'
    )

    @api.constrains('keywords')
    def _check_keywords(self):
        for record in self:
            if not record.keywords.strip():
                raise ValidationError(_('Debe ingresar al menos una palabra clave'))

    def get_keywords_list(self):
        """Retorna lista de palabras clave limpias"""
        if not self.keywords:
            return []
        return [kw.strip() for kw in self.keywords.strip().split('\n') if kw.strip()]

    @api.model
    def get_active_keywords(self, attendance_type):
        """Obtiene todas las palabras clave activas para un tipo de asistencia"""
        configs = self.search([
            ('active', '=', True),
            ('attendance_type', '=', attendance_type)
        ])

        all_keywords = []
        for config in configs:
            all_keywords.extend(config.get_keywords_list())

        return all_keywords

    @api.model
    def get_response_config(self, attendance_type):
        """Obtiene la configuración de respuesta para un tipo de asistencia"""
        config = self.search([
            ('active', '=', True),
            ('attendance_type', '=', attendance_type)
        ], limit=1)

        return config if config else None

    def get_response_message(self, employee_name, time, date, action):
        """Genera el mensaje de respuesta basado en la configuración"""
        if self.use_template and self.whatsapp_template_id:
            return self._format_whatsapp_template(employee_name, time, date, action)
        elif self.custom_message:
            return self._format_custom_message(employee_name, time, date, action)
        else:
            return self._get_default_message(employee_name, time, date, action)

    def _format_whatsapp_template(self, employee_name, time, date, action):
        """Formatea usando plantilla de WhatsApp"""
        template_body = getattr(self.whatsapp_template_id, 'body', '') or getattr(self.whatsapp_template_id, 'template_body', '')

        if not template_body:
            return self._get_default_message(employee_name, time, date, action)

        # Reemplazar variables en la plantilla
        message = template_body
        message = message.replace('{{1}}', employee_name)
        message = message.replace('{{2}}', action)
        message = message.replace('{{3}}', time)
        message = message.replace('{{4}}', date)

        return message

    def _format_custom_message(self, employee_name, time, date, action):
        """Formatea mensaje personalizado"""
        message = self.custom_message
        message = message.replace('{employee_name}', employee_name)
        message = message.replace('{time}', time)
        message = message.replace('{date}', date)
        message = message.replace('{action}', action)

        return message

    def _get_default_message(self, employee_name, time, date, action):
        """Mensaje por defecto si no hay configuración"""
        return f"✅ Hola {employee_name},\n\nTu *{action}* ha sido registrada correctamente.\n\n🕐 Hora: {time}\n📅 Fecha: {date}\n\n¡Que tengas un buen día!"
