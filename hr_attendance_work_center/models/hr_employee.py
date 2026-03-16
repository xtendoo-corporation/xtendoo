# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import exceptions, fields, models, _
from odoo.tools.image import image_data_uri


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def attendance_manual_work_center_force(self, next_action, work_center_id=None, location=None):
        if not location:
            location = self.env.context.get("attendance_location") or [0.0, 0.0]
        self.ensure_one()
        # Dedicated method to bypass any attendance permission checks in this custom flow.
        return self._attendance_action_work_center(next_action, work_center_id, location)

    def attendance_manual_work_center(self, next_action, work_center_id=None, entered_pin=None, location=None):
        return self.attendance_manual_work_center_force(next_action, work_center_id, location)


    def _attendance_action_work_center(self, next_action, work_center_id=None, location=None):
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        employee = self.sudo()
        action_message = self.env["ir.actions.actions"]._for_xml_id("hr_attendance.hr_attendance_action_greeting_message")

        if employee.user_id:
            modified_attendance = employee.with_user(employee.user_id)._attendance_action_change_work_center(work_center_id, location)
        else:
            modified_attendance = employee._attendance_action_change_work_center(work_center_id, location)

        overtime_today = self.env['hr.attendance.overtime'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date', '=', datetime.date.today()),
            ('adjustment', '=', False),
        ], limit=1).duration or 0

        action_message['previous_attendance_change_date'] = employee.last_attendance_id and (employee.last_attendance_id.check_out or employee.last_attendance_id.check_in) or False
        action_message['employee_name'] = employee.name
        action_message['employee_avatar'] = employee.image_256 and image_data_uri(employee.image_256)
        action_message['barcode'] = employee.barcode
        action_message['next_action'] = next_action
        action_message['hours_today'] = employee.hours_today
        action_message['kiosk_delay'] = employee.company_id.attendance_kiosk_delay * 1000
        action_message['display_overtime'] = employee.company_id.hr_attendance_display_overtime
        action_message['overtime_today'] = overtime_today
        action_message['attendance'] = modified_attendance.read()[0]
        action_message['total_overtime'] = employee.total_overtime
        return {'action': action_message}

    def _attendance_action_change_work_center(self, work_center_id=None, location=None):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        self.ensure_one()
        action_date = fields.Datetime.now()
        if self.attendance_state != 'checked_in':
            if work_center_id:
                # Accept both numeric ids and string payloads coming from JS actions.
                if isinstance(work_center_id, str):
                    work_center_id = int(work_center_id.replace(".", ""))
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
                'work_center_id': work_center_id,
                'in_latitude': location[0],
                'in_longitude': location[1],
            }
            return self.env['hr.attendance'].create(vals)
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_out', '=', False)],
                                                      limit=1)
        if attendance:
            attendance.check_out = action_date
            attendance.out_latitude = location[0]
            attendance.out_longitude = location[1]
        else:
            raise exceptions.UserError(
                _('Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                  'Your attendances have probably been modified manually by human resources.') % {
                    'empl_name': self.sudo().name, })
        return attendance
