# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

from odoo.addons.hr_attendance.controllers.main import HrAttendance


class HrAttendanceWorkCenterController(HrAttendance):
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

