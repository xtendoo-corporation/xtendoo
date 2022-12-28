# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    def attendance_manual_work_center(self, next_action, work_center_id=None, entered_pin=None, location=None):
        if not location:
            location=self.env.context.get("attendance_location", False)
        self.ensure_one()
        attendance_user_and_no_pin = self.user_has_groups(
            'hr_attendance.group_hr_attendance_user,'
            '!hr_attendance.group_hr_attendance_use_pin')
        can_check_without_pin = attendance_user_and_no_pin or (self.user_id == self.env.user and entered_pin is None)
        if can_check_without_pin or entered_pin is not None and entered_pin == self.sudo().pin:
            return self._attendance_action_work_center(next_action, work_center_id, location)
        if not self.user_has_groups('hr_attendance.group_hr_attendance_user'):
            return {'warning': _
                ('To activate Kiosk mode without pin code, you must have access right as an Officer or above in the Attendance app. Please contact your administrator.')}
        return {'warning': _('Wrong PIN')}

    def _attendance_action_work_center(self, next_action, work_center_id=None, location=None):
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        employee = self.sudo()
        action_message = self.env["ir.actions.actions"]._for_xml_id("hr_attendance.hr_attendance_action_greeting_message")
        action_message['previous_attendance_change_date'] = employee.last_attendance_id and (employee.last_attendance_id.check_out or employee.last_attendance_id.check_in) or False
        action_message['employee_name'] = employee.name
        action_message['barcode'] = employee.barcode
        action_message['next_action'] = next_action
        action_message['hours_today'] = employee.hours_today

        if employee.user_id:
            modified_attendance = employee.with_user(employee.user_id)._attendance_action_change_work_center(work_center_id, location)
        else:
            modified_attendance = employee._attendance_action_change_work_center(work_center_id,location)
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
                if "." in work_center_id:
                    work_center_id = work_center_id.replace(".", "")
                    work_center_id = int(work_center_id)
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
                'work_center_id': work_center_id,
                'check_in_latitude': location[0],
                'check_in_longitude': location[1],
            }
            return self.env['hr.attendance'].create(vals)
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_out', '=', False)],
                                                      limit=1)
        if attendance:
            attendance.check_out = action_date
            attendance.check_out_latitude = location[0]
            attendance.check_out_longitude = location[1]
        else:
            raise exceptions.UserError(
                _('Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                  'Your attendances have probably been modified manually by human resources.') % {
                    'empl_name': self.sudo().name, })
        return attendance
