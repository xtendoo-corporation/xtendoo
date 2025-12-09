from odoo import http
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

            telefono = data.get('telefono')
            pin = data.get('pin')
            latitud = data.get('latitud')
            longitud = data.get('longitud')

            print(f"Datos recibidos: telefono:{telefono}, pin:{pin}, latitud:{latitud}, longitud:{longitud}")

            if not pin or not telefono:
                print("pin o telefono no proporcionados")
                return request.make_json_response({'status': 'error', 'message': 'pin o telefono no proporcionados'})

            employee = request.env ['hr.employee'].sudo().search([('pin', "=", pin), ('phone', "=", telefono)], limit=1)

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
