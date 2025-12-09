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

            print(f"[DEBUG] Teléfono recibido (como char): '{telefono}' (type: {type(telefono)})")
            print(f"[DEBUG] PIN recibido (como char): '{pin}' (type: {type(pin)})")

            # Mostrar todos los empleados con su pin y teléfono
            all_employees = request.env['hr.employee'].sudo().search([])
            print("[DEBUG] Listado de todos los empleados (pin, teléfono):")
            for emp in all_employees:
                print(f"  - Empleado: {emp.name}, PIN: '{emp.pin}', Teléfono: '{emp.mobile_phone}'")

            if not pin or not telefono:
                print("pin o telefono no proporcionados")
                return request.make_json_response({'status': 'error', 'message': 'pin o telefono no proporcionados'})

            employee = request.env['hr.employee'].sudo().search([('pin', '=', pin), ('mobile_phone', '=', telefono)], limit=1)

            print(f"[DEBUG] Realizando búsqueda de empleado con PIN='{pin}' y Teléfono='{telefono}'")
            if not employee:
                print ("Empleado no encontrado")

            last_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            if last_attendance:
                # Registrar salida (Check-Out)
                last_attendance.sudo().write({
                    'check_out': fields.Datetime.now(),
                    # Opcional: Si tienes campos de latitud/longitud en hr.attendance, añádelos aquí.
                    # 'checkout_lat': latitud,
                    # 'checkout_lng': longitud,
                })
                action = 'Salida registrada'
            else:
                # Registrar entrada (Check-In)
                request.env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': fields.Datetime.now(),
                    # Opcional: Si tienes campos de latitud/longitud en hr.attendance, añádelos aquí.
                    # 'checkin_lat': latitud,
                    # 'checkin_lng': longitud,
                })
                action = 'Entrada registrada'
            return request.make_json_response({
                    'status': 'success',
                    'message': action,
                    'employee': employee.name,
                    'latitud': latitud,
                    'longitud': longitud
                })

        except Exception as e:
            return request.make_json_response({
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            })
