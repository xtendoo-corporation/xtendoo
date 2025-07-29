from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Campo para habilitar geolocalización en WhatsApp
    whatsapp_geotrack_enabled = fields.Boolean(
        string='Geolocalización WhatsApp',
        default=False,
        help='Si está activado, se solicitará y registrará la ubicación del empleado cuando registre asistencia por WhatsApp'
    )

    # Campos para almacenar la última ubicación conocida
    last_whatsapp_latitude = fields.Float(
        string='Última Latitud WhatsApp',
        digits=(10, 7),
        help='Última latitud registrada via WhatsApp'
    )

    last_whatsapp_longitude = fields.Float(
        string='Última Longitud WhatsApp',
        digits=(10, 7),
        help='Última longitud registrada via WhatsApp'
    )

    last_whatsapp_location_time = fields.Datetime(
        string='Última Ubicación WhatsApp',
        help='Fecha y hora de la última ubicación registrada via WhatsApp'
    )

    last_whatsapp_address = fields.Char(
        string='Última Dirección WhatsApp',
        help='Dirección aproximada de la última ubicación registrada'
    )


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Campos para almacenar la geolocalización de cada registro de asistencia
    whatsapp_latitude = fields.Float(
        string='Latitud WhatsApp',
        digits=(10, 7),
        help='Latitud donde se registró la asistencia via WhatsApp'
    )

    whatsapp_longitude = fields.Float(
        string='Longitud WhatsApp',
        digits=(10, 7),
        help='Longitud donde se registró la asistencia via WhatsApp'
    )

    whatsapp_location_address = fields.Char(
        string='Dirección WhatsApp',
        help='Dirección aproximada donde se registró la asistencia'
    )

    whatsapp_location_accuracy = fields.Float(
        string='Precisión Ubicación',
        help='Precisión de la ubicación en metros'
    )

    def action_open_google_maps(self):
        """
        Abre Google Maps con la ubicación del empleado en una nueva ventana
        """
        if not self.last_whatsapp_latitude or not self.last_whatsapp_longitude:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No hay ubicación registrada para este empleado',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # URL de Google Maps con las coordenadas
        google_maps_url = f"https://www.google.com/maps?q={self.last_whatsapp_latitude},{self.last_whatsapp_longitude}"

        return {
            'type': 'ir.actions.act_url',
            'url': google_maps_url,
            'target': 'new',
        }
