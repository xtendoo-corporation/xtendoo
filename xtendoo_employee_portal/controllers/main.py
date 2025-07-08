import logging
import werkzeug
import uuid
import json
from datetime import datetime, timedelta
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

class EmployeePortalController(http.Controller):

    @http.route('/employee/portal/login', type='http', auth='public', website=True)
    def employee_login(self, **kw):
        """Página de inicio de sesión para empleados"""
        return request.render('xtendoo_employee_portal.employee_login_template', {})

    @http.route('/employee/portal/authenticate', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def employee_authenticate(self, pin=None, **kw):
        """Autenticación de empleados mediante PIN"""
        if not pin or not pin.isdigit() or len(pin) != 4:
            return werkzeug.utils.redirect('/employee/portal/login?error=invalid_pin')

        # Buscar al empleado por PIN
        employee = request.env['hr.employee'].sudo().search([('employee_pin', '=', pin)], limit=1)
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login?error=wrong_pin')

        # Crear una nueva sesión para el empleado
        session_token = str(uuid.uuid4())
        request.env['employee.portal.session'].sudo().create({
            'employee_id': employee.id,
            'session_token': session_token
        })

        # Establecer la cookie de sesión
        redirect = werkzeug.utils.redirect('/employee/portal/dashboard')
        redirect.set_cookie('employee_session', session_token, max_age=8 * 60 * 60)
        return redirect

    def _get_employee_from_session(self):
        """Obtiene el empleado actual de la sesión"""
        session_token = request.httprequest.cookies.get('employee_session')
        if not session_token:
            return False

        employee = request.env['employee.portal.session'].sudo().validate_session(session_token)
        return employee

    def _get_available_features(self):
        """Determina qué funcionalidades están disponibles según los módulos instalados"""
        IrModule = request.env['ir.module.module'].sudo()
        return {
            'timesheet': IrModule.search([('name', '=', 'hr_timesheet'), ('state', '=', 'installed')], limit=1).id is not False,
        }

    @http.route('/employee/portal/dashboard', type='http', auth='public', website=True)
    def employee_dashboard(self, **kw):
        """Dashboard principal del portal de empleados"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        available_features = self._get_available_features()

        return request.render('xtendoo_employee_portal.employee_dashboard_template', {
            'employee': employee,
            'available_features': available_features,
        })

    @http.route('/employee/portal/attendance', type='http', auth='public', website=True)
    def employee_attendance(self, **kw):
        """Página para fichar entrada y salida"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        # Formatear la fecha y hora actual
        now = datetime.now()
        current_date = now.strftime('%d/%m/%Y')
        current_time = now.strftime('%H:%M:%S')

        return request.render('xtendoo_employee_portal.employee_attendance_template', {
            'employee': employee,
            'attendance': attendance,
            'current_date': current_date,
            'current_time': current_time,
        })

    @http.route('/employee/portal/attendance/check', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def employee_attendance_check(self, **kw):
        """Registra entrada o salida del empleado"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        if attendance:  # Check out
            attendance.sudo().write({'check_out': fields.Datetime.now()})
        else:  # Check in
            request.env['hr.attendance'].sudo().create({
                'employee_id': employee.id,
                'check_in': fields.Datetime.now()
            })

        return werkzeug.utils.redirect('/employee/portal/attendance')

    @http.route('/employee/portal/leaves', type='http', auth='public', website=True)
    def employee_leaves(self, **kw):
        """Página para ver y solicitar ausencias"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        leaves = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id)
        ])

        leave_types = request.env['hr.leave.type'].sudo().search([
            ('requires_allocation', '=', 'no')
        ])

        return request.render('xtendoo_employee_portal.employee_leaves_template', {
            'employee': employee,
            'leaves': leaves,
            'leave_types': leave_types
        })

    @http.route('/employee/portal/leaves/request', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def employee_leaves_request(self, leave_type_id=None, date_from=None, date_to=None, name=None, **kw):
        """Solicita una nueva ausencia"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        if leave_type_id and date_from and date_to and name:
            try:
                request.env['hr.leave'].sudo().create({
                    'holiday_status_id': int(leave_type_id),
                    'employee_id': employee.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'name': name
                })
            except Exception as e:
                return werkzeug.utils.redirect('/employee/portal/leaves?error=' + str(e))

        return werkzeug.utils.redirect('/employee/portal/leaves')

    @http.route('/employee/portal/resource/calendar', type='http', auth='public', website=True)
    def employee_calendar(self, **kw):
        """Página para ver las planificaciones del empleado"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        # Obtener los horarios del empleado para la semana actual
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Obtener entradas del calendario
        calendar_entries = []
        if employee.resource_calendar_id:
            calendar = employee.resource_calendar_id
            for day in range(7):
                date = start_of_week + timedelta(days=day)
                intervals = calendar._work_intervals_batch(
                    datetime.combine(date, datetime.min.time()),
                    datetime.combine(date, datetime.max.time()),
                    resources=employee.resource_id
                )[employee.resource_id.id]

                day_entries = []
                for interval in intervals:
                    day_entries.append({
                        'start': interval[0].strftime('%H:%M'),
                        'end': interval[1].strftime('%H:%M')
                    })

                calendar_entries.append({
                    'day': date.strftime('%d-%m-%Y'),
                    'day_name': date.strftime('%A'),
                    'intervals': day_entries
                })

        return request.render('xtendoo_employee_portal.employee_calendar_template', {
            'employee': employee,
            'calendar_entries': calendar_entries
        })

    @http.route('/employee/portal/timesheets', type='http', auth='public', website=True)
    def employee_timesheets(self, **kw):
        """Página para ver los partes de horas del empleado"""
        # Verificar si el módulo hr_timesheet está instalado
        if not self._get_available_features()['timesheet']:
            return werkzeug.utils.redirect('/employee/portal/dashboard')

        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        # Obtener partes de horas del mes actual
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_of_month = next_month.replace(day=1) - timedelta(days=1)

        timesheets = request.env['account.analytic.line'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date', '>=', start_of_month),
            ('date', '<=', end_of_month)
        ], order='date desc') if self._get_available_features()['timesheet'] else []

        return request.render('xtendoo_employee_portal.employee_timesheets_template', {
            'employee': employee,
            'timesheets': timesheets,
            'available_features': self._get_available_features(),
        })

    @http.route('/employee/portal/attendance/history', type='http', auth='public', website=True)
    def employee_attendance_history(self, **kw):
        """Página para ver el historial de registros de entradas y salidas"""
        employee = self._get_employee_from_session()
        if not employee:
            return werkzeug.utils.redirect('/employee/portal/login')

        # Obtener registros de asistencia del mes actual
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_of_month = next_month.replace(day=1) - timedelta(days=1)

        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', datetime.combine(start_of_month, datetime.min.time())),
            ('check_in', '<=', datetime.combine(end_of_month, datetime.max.time()))
        ], order='check_in desc')

        return request.render('xtendoo_employee_portal.employee_attendance_history_template', {
            'employee': employee,
            'attendances': attendances
        })

    @http.route('/employee/portal/logout', type='http', auth='public', website=True)
    def employee_logout(self, **kw):
        """Cierra la sesión del empleado"""
        session_token = request.httprequest.cookies.get('employee_session')
        if session_token:
            sessions = request.env['employee.portal.session'].sudo().search([
                ('session_token', '=', session_token)
            ])
            sessions.unlink()

        redirect = werkzeug.utils.redirect('/employee/portal/login')
        redirect.delete_cookie('employee_session')
        return redirect
