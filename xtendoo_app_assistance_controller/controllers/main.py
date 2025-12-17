from odoo import http, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class XtendooAppAssistanceController(http.Controller):

    @http.route('/xtendoo/app/assistance', auth='public', type='http', methods=['POST'], csrf=False)
    def assistance(self, **kwargs):
        try:
            raw = request.httprequest.data.decode('utf-8')
            data = json.loads(raw)
            _logger.info(f"Datos recibidos: {data}")

            telefono_formatear = str(data.get('telefono', ''))
            telefono = telefono_formatear.replace(" ", "")
            pin = str(data.get('pin', ''))
            latitud = data.get('latitud')
            longitud = data.get('longitud')

            if not pin or not telefono:
                return request.make_json_response({
                    'status': 'error',
                    'message': 'PIN o teléfono no proporcionados'
                })

            #_logger.info("=== LISTADO DE EMPLEADOS PARA DEBUG ===")
            #all_employees = request.env['hr.employee'].sudo().search([])
            #for emp in all_employees:
                #_logger.info(f"Empleado: {emp.name} | PIN: '{emp.pin}' | Teléfono: '{emp.mobile_phone}'")
            #_logger.info("=== FIN LISTADO ===")


            employees = request.env['hr.employee'].sudo().search([ ('pin', '=', pin) ])
            employee = None
            for emp in employees:
                mobile_db = str(emp.mobile_phone or '').replace(" ", "")
                if mobile_db == telefono:
                    employee = emp
                    break


            if not employee:
                _logger.error(f"Empleado no encontrado con PIN='{pin}' y Teléfono='{telefono}'")
                return request.make_json_response({
                    'status': 'error',
                    'message': 'Empleado no encontrado'
                })

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

            return request.make_json_response({
                'status': 'success',
                'message': action,
                'employee': employee.name,
                'latitud': latitud,
                'longitud': longitud
            })

        except Exception as e:
            _logger.error(f"Error en assistance: {str(e)}", exc_info=True)
            return request.make_json_response({
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            })


    @http.route('/xtendoo/app/get_status', auth='public', type='http', methods=['POST'], csrf=False)
    def get_employee_status(self, **kwargs):
        """
        Consulta el estado de asistencia actual del empleado (dentro/fuera).
        No realiza ninguna acción de fichaje.
        """
        try:
            raw = request.httprequest.data.decode('utf-8')
            data = json.loads(raw)
            _logger.info(f"Datos recibidos para consulta de estado: {data}")

            telefono_formatear = str(data.get('telefono', ''))
            telefono = telefono_formatear.replace(" ", "")
            pin = str(data.get('pin', ''))

            if not pin or not telefono:
                return request.make_json_response({
                    'status': 'error',
                    'message': 'PIN o teléfono no proporcionados'
                })

            employees = request.env['hr.employee'].sudo().search([
                ('pin', '=', pin)
            ])

            employee = None
            for emp in employees:
                mobile_db = str(emp.mobile_phone or '').replace(" ", "")
                if mobile_db == telefono:
                    employee = emp
                    break

            if not employee:
                _logger.error(f"Empleado no encontrado con PIN='{pin}' y Teléfono='{telefono}'")
                return request.make_json_response({
                    'status': 'error',
                    'message': 'Empleado no encontrado'
                })


            last_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)


            is_inside = bool(last_attendance)



            message = 'Empleado actualmente fichado dentro.' if is_inside else 'Empleado actualmente fichado fuera.'

            return request.make_json_response({
                'status': 'success',
                'is_inside': is_inside,
                'message': message,
                'employee': employee.name,
            })

        except Exception as e:
            _logger.error(f"Error en get_employee_status: {str(e)}", exc_info=True)
            return request.make_json_response({
                'status': 'error',
                'message': f'Error interno del servidor: {str(e)}'
            })
