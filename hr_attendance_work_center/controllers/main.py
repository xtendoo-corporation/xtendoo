# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

from odoo.addons.hr_attendance.controllers.main import HrAttendance


class HrAttendanceWorkCenterController(HrAttendance):
    @staticmethod
    def _employee_internal_payload(employee):
        attendance = employee.last_attendance_id
        work_center = attendance.work_center_id if attendance else False
        return {
            "id": employee.id,
            "name": employee.name,
            "attendance_state": employee.attendance_state,
            "hours_today": employee.hours_today,
            "has_pin": bool(employee.pin),
            "work_center_name": work_center.name if work_center else False,
            "work_center_id": work_center.id if work_center else False,
            "avatar_url": f"/web/image/hr.employee/{employee.id}/avatar_128",
        }

    @staticmethod
    def _allowed_company_domain():
        return [("company_id", "in", request.env.user.company_ids.ids)]

    def _get_employee_for_internal_flow(self, employee_id=False):
        user_employee = request.env.user.employee_id.sudo()
        if user_employee:
            if employee_id and int(employee_id) != user_employee.id:
                raise UserError("No puede fichar por otro empleado.")
            return user_employee, False

        if not employee_id:
            raise UserError("Debe seleccionar un empleado.")

        employee = request.env["hr.employee"].sudo().browse(int(employee_id)).exists()
        if not employee or employee.company_id.id not in request.env.user.company_ids.ids:
            raise UserError("Empleado no valido para esta compania.")
        return employee, True

    def _check_pin_if_required(self, employee, pin_code, pin_required):
        if not pin_required:
            return
        # 🔴 Nuevo: obligar a que tenga PIN
        if not employee.pin:
            raise UserError("El empleado no tiene PIN configurado.")

        if pin_code in (False, None, ""):
            print("*"*50)
            print("pin_Required", pin_required)
            raise UserError("Debe introducir el PIN.")

        if str(employee.pin or "") != str(pin_code or ""):
            raise UserError("PIN incorrecto.")

    @staticmethod
    def _response_with_work_center(employee, attendance=None):
        response = HrAttendance._get_employee_info_response(employee)
        target_attendance = attendance or employee.last_attendance_id
        work_center = target_attendance.work_center_id if target_attendance else False
        response["work_center_name"] = work_center.name if work_center else False
        response["work_center_id"] = work_center.id if work_center else False
        return response

    @staticmethod
    def _location(latitude=False, longitude=False):
        lat = float(latitude) if latitude not in (False, None, "") else 0.0
        lon = float(longitude) if longitude not in (False, None, "") else 0.0
        return [lat, lon]

    @http.route('/hr_attendance/internal/bootstrap', type="json", auth="user")
    def internal_bootstrap(self):
        user_employee = request.env.user.employee_id.sudo()
        work_centers = request.env["res.partner"].sudo().search_read(
            [("is_work_center", "=", True)],
            ["id", "display_name", "city", "country_id", "avatar_128"],
            order="name asc, id asc",
        )
        return {
            "requires_employee_selection": not bool(user_employee),
            "employee": self._employee_internal_payload(user_employee) if user_employee else False,
            "work_centers": work_centers,
        }

    @http.route('/hr_attendance/internal/employees', type="json", auth="user")
    def internal_employees(self):
        employees = request.env["hr.employee"].sudo().search(
            self._allowed_company_domain(),
            order="name asc, id asc",
        )

        return {
            "records": [
                {
                    "id": emp.id,
                    "name": emp.name,
                    "attendance_state": emp.attendance_state,
                    "hours_today": emp.hours_today,
                    "has_pin": bool(emp.pin),
                    "avatar_url": f"/web/image/hr.employee/{emp.id}/avatar_128",
                }
                for emp in employees
            ]
        }

    @http.route('/hr_attendance/internal/attendance_action', type="json", auth="user")
    def internal_attendance_action(self, employee_id=False, work_center_id=False, pin_code=False, latitude=False, longitude=False):
        employee, pin_required = self._get_employee_for_internal_flow(employee_id)
        self._check_pin_if_required(employee, pin_code, pin_required)

        location = self._location(latitude=latitude, longitude=longitude)
        attendance = employee._attendance_action_change_work_center(work_center_id, location)
        return self._response_with_work_center(employee, attendance)

    @http.route('/hr_attendance/work_centers', type="json", auth="public")
    def work_centers(self, token):
        company = self._get_company(token)
        if not company:
            return {"records": []}
        records = request.env["res.partner"].sudo().search_read(
            [("is_work_center", "=", True)],
            ["id", "display_name", "city", "country_id", "avatar_128"],
            order="name asc, id asc",
        )
        return {"records": records}

    @http.route('/hr_attendance/manual_selection', type="json", auth="public")
    def manual_selection_with_geolocation(self, token, employee_id, pin_code, latitude=False, longitude=False):
        company = self._get_company(token)
        if not company:
            return {}

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if employee.company_id != company:
            return {}

        if company.attendance_kiosk_use_pin and employee.pin != pin_code:
            return {}

        location = self._location(latitude=latitude, longitude=longitude)
        if employee.attendance_state == 'checked_in':
            attendance = employee._attendance_action_change_work_center(False, location)
            return self._response_with_work_center(employee, attendance)

        return {
            "needs_work_center": True,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "use_pin": company.attendance_kiosk_use_pin,
            "pin_code": pin_code,
        }

    @http.route('/hr_attendance/manual_selection_work_center', type="json", auth="public")
    def manual_selection_work_center(self, token, employee_id, work_center_id, pin_code=False, latitude=False, longitude=False):
        company = self._get_company(token)
        if not company:
            return {}

        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if employee.company_id != company:
            return {}

        if company.attendance_kiosk_use_pin and employee.pin != pin_code:
            return {}

        location = self._location(latitude=latitude, longitude=longitude)
        attendance = employee._attendance_action_change_work_center(work_center_id, location)
        return self._response_with_work_center(employee, attendance)

    @http.route('/hr_attendance/attendance_barcode_scanned', type="json", auth="public")
    def scan_barcode(self, token, barcode):
        company = self._get_company(token)
        if not company:
            return {}

        employee = request.env['hr.employee'].sudo().search(
            [('barcode', '=', barcode), ('company_id', '=', company.id)],
            limit=1,
        )
        if not employee:
            return {}

        if employee.attendance_state == 'checked_in':
            attendance = employee._attendance_action_change_work_center(False, [0.0, 0.0])
            return self._response_with_work_center(employee, attendance)

        return {
            "needs_work_center": True,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "barcode": barcode,
        }

