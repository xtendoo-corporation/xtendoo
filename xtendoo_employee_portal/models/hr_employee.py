from odoo import fields, models, api
from odoo.exceptions import ValidationError
import re


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_pin = fields.Char(
        string="PIN de Empleado",
        help="PIN para iniciar sesión en el portal de empleados",
        copy=False,
        groups="hr.group_hr_user",
    )

    # Campo para compatibilidad con hr_timesheet
    timesheet_manager_id = fields.Many2one(
        'hr.employee',
        string='Timesheet Manager',
        compute='_compute_timesheet_manager_id',
        store=False,
        help='Dummy field for compatibility with hr_timesheet'
    )

    @api.constrains("employee_pin")
    def _check_employee_pin(self):
        for employee in self:
            if employee.employee_pin:
                # Verificar que el PIN tenga 4 dígitos numéricos
                if not re.match(r"^\d{4}$", employee.employee_pin):
                    raise ValidationError("El PIN del empleado debe contener exactamente 4 dígitos.")

                # Verificar que el PIN sea único
                same_pin = self.search([
                    ('id', '!=', employee.id),
                    ('employee_pin', '=', employee.employee_pin)
                ])
                if same_pin:
                    raise ValidationError("Este PIN ya está siendo utilizado por otro empleado.")

    @api.depends()
    def _compute_timesheet_manager_id(self):
        """Campo calculado para compatibilidad con hr_timesheet"""
        for employee in self:
            employee.timesheet_manager_id = False
