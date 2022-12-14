# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    work_center_id = fields.Many2one('res.partner', string="Work Center", required=True, ondelete='cascade', index=True)

    @api.model
    def get_default_employee(self):
        data = {}
        if self.env.user.employee_id:
            data['id'] = self.env.user.employee_id.id
            data['name'] = self.env.user.employee_id.name
        return data


