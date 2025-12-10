from odoo import http, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class XtendooAppAssistanceController(http.Controller):
    #cambiamos a http pra ver si funciona en vez de json
    @http.route('/xtendoo/app/assistance', auth='public', type='json', methods=['POST'], csrf=False)
    def assistance(self, **kwargs):
        try:
            raw = request.httprequest.data.decode('utf-8')
            data = json.loads(raw)
            print(f"Datos recibidos: {data}")

            telefono = str(data.get('telefono', ''))
            pin = str(data.get('pin', ''))
            latitud = data.get('latitud')
            longitud = data.get('longitud')

            print(f"[DEBUG] Teléfono: '{telefono}', PIN: '{pin}'")

            if not pin or not telefono:
                return {'status': 'error', 'message': 'PIN o teléfono no proporcionados'}

            employee = request.env['hr.employee'].sudo().search([
                ('pin', '=', pin),
                ('mobile_phone', '=', telefono)
            ], limit=1)

            if not employee:  # ✅ IMPORTANTE: Verificar antes de continuar
                print(f"[ERROR] Empleado no encontrado con PIN='{pin}' y Teléfono='{telefono}'")
                return {'status': 'error', 'message': 'Empleado no encontrado'}

            last_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            if last_attendance:
                last_attendance.sudo().write({
                    'check_out': fields.Datetime.now(),
                })
                action = 'Salida registrada'
            else:
                request.env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': fields.Datetime.now(),
                })
                action = 'Entrada registrada'

            return {
                'status': 'success',
                'message': action,
                'employee': employee.name,
                'latitud': latitud,
                'longitud': longitud
            }

        except Exception as e:
            _logger.error(f"Error en assistance: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            }
