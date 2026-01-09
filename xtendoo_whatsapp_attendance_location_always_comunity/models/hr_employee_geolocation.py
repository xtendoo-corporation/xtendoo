# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # En este módulo, la geolocalización está activada por defecto
    whatsapp_geotrack_enabled = fields.Boolean(
        string='Geolocalización WhatsApp',
        default=True,
        help='Si está activado, se solicitará y registrará la ubicación del empleado cuando registre asistencia por WhatsApp. En este módulo está activado por defecto.'
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

    def action_open_google_maps_check_in(self):
        """
        Abre Google Maps con la ubicación de entrada de esta asistencia
        """
        if not self.whatsapp_check_in_latitude or not self.whatsapp_check_in_longitude:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No hay ubicación de entrada registrada',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        google_maps_url = f"https://www.google.com/maps?q={self.whatsapp_check_in_latitude},{self.whatsapp_check_in_longitude}"

        return {
            'type': 'ir.actions.act_url',
            'url': google_maps_url,
            'target': 'new',
        }

    def action_open_google_maps_check_out(self):
        """
        Abre Google Maps con la ubicación de salida de esta asistencia
        """
        if not self.whatsapp_check_out_latitude or not self.whatsapp_check_out_longitude:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No hay ubicación de salida registrada',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        google_maps_url = f"https://www.google.com/maps?q={self.whatsapp_check_out_latitude},{self.whatsapp_check_out_longitude}"

        return {
            'type': 'ir.actions.act_url',
            'url': google_maps_url,
            'target': 'new',
        }

