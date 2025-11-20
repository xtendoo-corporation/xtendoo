from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Campo para habilitar geolocalización en WhatsApp
    whatsapp_geotrack_enabled = fields.Boolean(
        string='Geolocalización WhatsApp',
        default=True,
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

    # Campos para almacenar la geolocalización de la entrada
    whatsapp_check_in_latitude = fields.Float(
        string='Latitud Entrada WhatsApp',
        digits=(10, 7),
        help='Latitud donde se registró la entrada via WhatsApp'
    )
    whatsapp_check_in_longitude = fields.Float(
        string='Longitud Entrada WhatsApp',
        digits=(10, 7),
        help='Longitud donde se registró la entrada via WhatsApp'
    )
    whatsapp_check_in_location_address = fields.Char(
        string='Dirección Entrada WhatsApp',
        help='Dirección aproximada donde se registró la entrada'
    )
    whatsapp_check_in_location_accuracy = fields.Float(
        string='Precisión Entrada Ubicación',
        help='Precisión de la ubicación de entrada en metros'
    )

    # Campos para almacenar la geolocalización de la salida
    whatsapp_check_out_latitude = fields.Float(
        string='Latitud Salida WhatsApp',
        digits=(10, 7),
        help='Latitud donde se registró la salida via WhatsApp'
    )
    whatsapp_check_out_longitude = fields.Float(
        string='Longitud Salida WhatsApp',
        digits=(10, 7),
        help='Longitud donde se registró la salida via WhatsApp'
    )
    whatsapp_check_out_location_address = fields.Char(
        string='Dirección Salida WhatsApp',
        help='Dirección aproximada donde se registró la salida'
    )
    whatsapp_check_out_location_accuracy = fields.Float(
        string='Precisión Salida Ubicación',
        help='Precisión de la ubicación de salida en metros'
    )

    # Los campos antiguos se mantienen para compatibilidad, pero se recomienda usar los nuevos
    whatsapp_location_address = fields.Char(
        string='Dirección WhatsApp',
        help='Dirección aproximada donde se registró la asistencia'
    )
    whatsapp_location_accuracy = fields.Float(
        string='Precisión Ubicación',
        help='Precisión de la ubicación en metros'
    )

    def action_open_google_maps(self, check_type='in'):
        """
        Abre Google Maps con la ubicación de entrada o salida de esta asistencia específica
        """
        lat = self.whatsapp_check_in_latitude if check_type == 'in' else self.whatsapp_check_out_latitude
        lon = self.whatsapp_check_in_longitude if check_type == 'in' else self.whatsapp_check_out_longitude
        if not lat or not lon:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No hay ubicación registrada para esta asistencia',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        return {
            'type': 'ir.actions.act_url',
            'url': google_maps_url,
            'target': 'new',
        }
