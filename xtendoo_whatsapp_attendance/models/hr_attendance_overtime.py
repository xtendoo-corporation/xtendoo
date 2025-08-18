from odoo import models, api

class HrAttendanceOvertimeInherited(models.Model):
    _inherit = "hr.attendance.overtime"

    @api.model
    def create(self, vals):
        if not vals.get('adjustment', False):
            domain = [
                ('employee_id', '=', vals.get('employee_id')),
                ('date', '=', vals.get('date')),
                ('adjustment', '=', False)
            ]
            existing = self.search(domain, limit=1)
            if existing:
                existing.write(vals)
                return existing
        return super().create(vals)
