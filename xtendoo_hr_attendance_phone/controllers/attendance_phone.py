import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AttendancePhone(http.Controller):

    @http.route('/attendance/phone', type='http', auth='public', website=True)
    def attendance_phone(self):
        """Página web para registro de asistencia por teléfono"""
        _logger.info("[ATTENDANCE_PHONE] Acceso a página de asistencia por teléfono")
        return request.render('xtendoo_hr_attendance_phone.attendance_phone_page')

    @http.route('/attendance/phone/mobile', type='http', auth='public', website=True)
    def attendance_phone_mobile(self):
        """Página web móvil para registro de asistencia por teléfono"""
        _logger.info("[ATTENDANCE_PHONE] Acceso a página móvil de asistencia")
        return request.render('xtendoo_hr_attendance_phone.attendance_phone_mobile_page')

    @http.route('/hr_attendance/set_settings', type='jsonrpc', auth='public', csrf=False)
    def set_attendance_settings(self, token, mode, **kwargs):
        """
        Configura el modo de asistencia del kiosco

        Args:
            token (str): Token del kiosco
            mode (str): Modo de kiosco ('phone', 'manual', 'barcode', etc.)

        Returns:
            dict: Resultado de la configuración
        """
        _logger.info("[ATTENDANCE_PHONE] Configurando modo kiosco: %s", mode)

        try:
            # Obtener la empresa por token
            company = request.env['res.company'].sudo().search([
                ('attendance_kiosk_key', '=', token)
            ], limit=1)

            if not company:
                _logger.warning("[ATTENDANCE_PHONE] Token de kiosco inválido: %s", token)
                return {"success": False, "error": "Token inválido"}

            # Validar que el modo sea válido
            valid_modes = ['phone', 'phone_only', 'manual', 'barcode', 'barcode_manual']
            if mode not in valid_modes:
                _logger.warning("[ATTENDANCE_PHONE] Modo inválido: %s", mode)
                return {"success": False, "error": f"Modo inválido: {mode}"}

            # Configurar el modo
            company.write({'attendance_kiosk_mode': mode})
            _logger.info("[ATTENDANCE_PHONE] Modo configurado exitosamente: %s para empresa %s",
                        mode, company.name)

            return {
                "success": True,
                "mode": mode,
                "company": company.name
            }

        except Exception as e:
            _logger.error("[ATTENDANCE_PHONE] Error configurando modo: %s", str(e))
            return {"success": False, "error": str(e)}

    @http.route('/attendance/phone/validate_phone_only', type='jsonrpc', auth='public', csrf=False)
    def validate_employee_phone_only(self, phone, token=None, **kwargs):
        """
        Valida empleado SOLO por teléfono (sin PIN), registra asistencia

        Args:
            phone (str): Número de teléfono del empleado
            token (str, optional): Token del kiosco para validación

        Returns:
            dict: Resultado de la validación y registro
        """
        _logger.info("[ATTENDANCE_PHONE_ONLY] Validación solo teléfono - Teléfono: %s***", phone[:3] if phone else 'N/A')

        try:
            if not phone:
                _logger.warning("[ATTENDANCE_PHONE_ONLY] Teléfono faltante")
                return {"success": False, "error": "Número de teléfono requerido"}

            # Limpiar el número de teléfono
            phone_cleaned = ''.join(filter(str.isdigit, phone.replace('+', '')))
            _logger.info("[ATTENDANCE_PHONE_ONLY] Teléfono limpiado: %s***", phone_cleaned[:3] if len(phone_cleaned) >= 3 else phone_cleaned)

            # Buscar empleado por teléfono de forma más directa
            all_employees = request.env['hr.employee'].sudo().search([])
            employee = None

            for emp in all_employees:
                # Obtener teléfonos del empleado y limpiarlos
                mobile_clean = ''.join(filter(str.isdigit, (emp.mobile_phone or '').replace('+', '')))
                work_clean = ''.join(filter(str.isdigit, (emp.work_phone or '').replace('+', '')))

                # Comparar números limpios
                if mobile_clean == phone_cleaned or work_clean == phone_cleaned:
                    employee = emp
                    _logger.info("[ATTENDANCE_PHONE_ONLY] ✅ Empleado encontrado: %s", emp.name)
                    break

            if not employee:
                _logger.warning("[ATTENDANCE_PHONE_ONLY] No se encontró empleado con el teléfono")
                return {"success": False, "error": "Teléfono no registrado"}

            _logger.info("[ATTENDANCE_PHONE_ONLY] Empleado encontrado: %s (ID: %s)", employee.name, employee.id)

            # Determinar si será entrada o salida ANTES de cambiar
            current_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            action_type = 'check_out' if current_attendance else 'check_in'
            _logger.info("[ATTENDANCE_PHONE_ONLY] Acción a realizar: %s", action_type)

            # Registrar asistencia sin parámetros adicionales
            try:
                employee.sudo()._attendance_action_change()
                _logger.info("[ATTENDANCE_PHONE_ONLY] ✅ Asistencia registrada para %s", employee.name)
            except Exception as attendance_error:
                _logger.error("[ATTENDANCE_PHONE_ONLY] Error registrando asistencia: %s", str(attendance_error))
                raise

            return {
                "success": True,
                "employee_id": employee.id,
                "name": employee.name,
                "action_type": action_type
            }

        except Exception as e:
            _logger.error("[ATTENDANCE_PHONE_ONLY] Error: %s", str(e))
            return {"success": False, "error": f"Error del servidor: {str(e)}"}

    @http.route('/attendance/phone/validate', type='jsonrpc', auth='public', csrf=False)
    def validate_employee(self, phone, pin, token=None, **kwargs):
        """Valida empleado por teléfono y PIN, registra asistencia"""
        _logger.info("[ATTENDANCE_PHONE] Iniciando validación - Teléfono: %s***", phone[:3] if phone else 'N/A')

        try:

            if not phone or not pin:
                _logger.warning("[ATTENDANCE_PHONE] Parámetros faltantes - Phone: %s, Pin: %s",
                              bool(phone), bool(pin))
                return {"success": False, "error": "Parámetros requeridos faltantes"}

            # Limpiar el número de teléfono (remover espacios, guiones, etc.)
            phone_cleaned = ''.join(filter(str.isdigit, phone.replace('+', '')))

            # Buscar empleado por PIN primero
            employees_with_pin = request.env['hr.employee'].sudo().search([('pin', '=', pin)])
            _logger.info("[ATTENDANCE_PHONE] Empleados encontrados con PIN %s: %s", pin, len(employees_with_pin))

            # Verificar teléfono
            employee = None
            for emp in employees_with_pin:
                mobile_clean = ''.join(filter(str.isdigit, (emp.mobile_phone or '').replace('+', '')))
                work_clean = ''.join(filter(str.isdigit, (emp.work_phone or '').replace('+', '')))

                if mobile_clean == phone_cleaned or work_clean == phone_cleaned:
                    employee = emp
                    _logger.info("[ATTENDANCE_PHONE] ✅ Coincidencia encontrada con empleado %s", emp.name)
                    break

            if not employee:
                return {"success": False, "error": "PIN o teléfono incorrecto"}

            # Determinar si será entrada o salida ANTES de cambiar
            # Si el empleado tiene una asistencia abierta (sin check_out), será salida
            current_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            # Si hay asistencia abierta, será check_out; si no, será check_in
            action_type = 'check_out' if current_attendance else 'check_in'
            _logger.info("[ATTENDANCE_PHONE] Acción a realizar: %s", action_type)

            # Registrar asistencia
            try:
                result = employee.sudo()._attendance_action_change()
                _logger.info("[ATTENDANCE_PHONE] ✅ Asistencia registrada exitosamente para %s", employee.name)

                return {
                    "success": True,
                    "employee_id": employee.id,
                    "name": employee.name,
                    "action_type": action_type
                }

            except Exception as attendance_error:
                _logger.error("[ATTENDANCE_PHONE] Error al registrar asistencia: %s", str(attendance_error))
                return {"success": False, "error": f"Error al registrar asistencia: {str(attendance_error)}"}

        except Exception as e:
            _logger.error("[ATTENDANCE_PHONE] Error: %s", str(e))
            return {"success": False, "error": f"Error del servidor: {str(e)}"}

    @http.route('/attendance/phone/status', type='jsonrpc', auth='public', csrf=False)
    def get_employee_status(self, phone, **kwargs):
        """
        Consulta el estado actual del empleado (dentro/fuera) basado en su teléfono

        Args:
            phone (str): Número de teléfono del empleado

        Returns:
            dict: Estado del empleado
        """
        _logger.info("[ATTENDANCE_PHONE_STATUS] Consultando estado - Teléfono: %s***", phone[:3] if phone else 'N/A')

        try:
            if not phone:
                return {"success": False, "error": "Teléfono requerido"}

            # Limpiar el número de teléfono
            phone_cleaned = ''.join(filter(str.isdigit, phone.replace('+', '')))
            _logger.info("[ATTENDANCE_PHONE_STATUS] Teléfono limpiado: %s***", phone_cleaned[:3] if len(phone_cleaned) >= 3 else phone_cleaned)

            # Buscar empleado por teléfono
            all_employees = request.env['hr.employee'].sudo().search([])
            employee = None

            for emp in all_employees:
                mobile_clean = ''.join(filter(str.isdigit, (emp.mobile_phone or '').replace('+', '')))
                work_clean = ''.join(filter(str.isdigit, (emp.work_phone or '').replace('+', '')))

                if mobile_clean == phone_cleaned or work_clean == phone_cleaned:
                    employee = emp
                    _logger.info("[ATTENDANCE_PHONE_STATUS] ✅ Empleado encontrado: %s", emp.name)
                    break

            if not employee:
                return {"success": False, "error": "Empleado no encontrado"}

            # Verificar si tiene asistencia abierta (está trabajando)
            current_attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            if current_attendance:
                status = "DENTRO"
                status_class = "success"
                message = f"{employee.name}: En línea"
                _logger.info("[ATTENDANCE_PHONE_STATUS] Empleado DENTRO desde: %s", current_attendance.check_in)
            else:
                status = "FUERA"
                status_class = "warning"
                message = f"{employee.name}: Ausente"
                _logger.info("[ATTENDANCE_PHONE_STATUS] Empleado FUERA")

            return {
                "success": True,
                "employee_id": employee.id,
                "name": employee.name,
                "status": status,
                "status_class": status_class,
                "message": message
            }

        except Exception as e:
            _logger.error("[ATTENDANCE_PHONE_STATUS] Error: %s", str(e))
            return {"success": False, "error": f"Error del servidor: {str(e)}"}


    @http.route('/attendance/phone/register', type='jsonrpc', auth='public', csrf=False)
    def register_employee_phone(self, employee_pin, phone_number, **kwargs):
        """
        Registra el número de teléfono del empleado la primera vez.
        El empleado se identifica solo por PIN y luego se guarda su teléfono.

        Args:
            employee_pin (str): PIN del empleado (ya configurado en Odoo)
            phone_number (str): Número de teléfono a registrar

        Returns:
            dict: Resultado del registro
        """
        _logger.info("[ATTENDANCE_PHONE] Registro de teléfono - PIN: ***")

        try:
            if not employee_pin or not phone_number:
                return {"success": False, "error": "PIN y teléfono son requeridos"}

            # Buscar empleado solo por PIN
            employee = request.env['hr.employee'].sudo().search([
                ('pin', '=', employee_pin)
            ], limit=1)

            if not employee:
                _logger.warning("[ATTENDANCE_PHONE] No se encontró empleado con el PIN proporcionado")
                return {"success": False, "error": "PIN incorrecto"}

            # Limpiar el número de teléfono
            phone_cleaned = ''.join(filter(str.isdigit, phone_number.replace('+', '')))

            # Verificar si el teléfono ya está registrado para otro empleado
            existing = request.env['hr.employee'].sudo().search([
                ('id', '!=', employee.id),
                '|',
                ('mobile_phone', 'ilike', phone_cleaned),
                ('work_phone', 'ilike', phone_cleaned)
            ], limit=1)

            if existing:
                _logger.warning("[ATTENDANCE_PHONE] El teléfono ya está registrado para otro empleado")
                return {"success": False, "error": "Este teléfono ya está registrado para otro empleado"}

            # Guardar el teléfono en el campo mobile_phone si está vacío, sino en work_phone
            if not employee.mobile_phone:
                employee.sudo().write({'mobile_phone': phone_number})
                _logger.info("[ATTENDANCE_PHONE] Teléfono registrado en mobile_phone para empleado %s", employee.name)
            elif not employee.work_phone:
                employee.sudo().write({'work_phone': phone_number})
                _logger.info("[ATTENDANCE_PHONE] Teléfono registrado en work_phone para empleado %s", employee.name)
            else:
                # Si ambos campos están ocupados, actualizar mobile_phone
                employee.sudo().write({'mobile_phone': phone_number})
                _logger.info("[ATTENDANCE_PHONE] Teléfono actualizado en mobile_phone para empleado %s", employee.name)

            return {
                "success": True,
                "employee_id": employee.id,
                "name": employee.name,
                "message": f"Teléfono registrado exitosamente para {employee.name}"
            }

        except Exception as e:
            _logger.error("[ATTENDANCE_PHONE] Error registrando teléfono: %s", str(e))
            return {
                "success": False,
                "error": f"Error del servidor: {str(e)}"
            }

    @http.route('/attendance/phone/check-registration', type='jsonrpc', auth='public', csrf=False)
    def check_employee_registration(self, phone_number, **kwargs):
        """
        Verifica si un número de teléfono ya está registrado

        Args:
            phone_number (str): Número de teléfono a verificar

        Returns:
            dict: Estado de registro del teléfono
        """
        try:
            if not phone_number:
                return {"registered": False, "error": "Teléfono requerido"}

            phone_cleaned = ''.join(filter(str.isdigit, phone_number.replace('+', '')))

            employee = request.env['hr.employee'].sudo().search([
                '|',
                ('mobile_phone', 'ilike', phone_cleaned),
                ('work_phone', 'ilike', phone_cleaned)
            ], limit=1)

            if employee:
                return {
                    "registered": True,
                    "employee_name": employee.name,
                    "has_pin": bool(employee.pin)
                }

            return {"registered": False}

        except Exception as e:
            _logger.error("[ATTENDANCE_PHONE] Error verificando registro: %s", str(e))
            return {"registered": False, "error": str(e)}

