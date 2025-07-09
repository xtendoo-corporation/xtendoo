from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Employee(models.Model):
    _inherit = 'hr.employee'

    pin = fields.Char(
        string="PIN de acceso portal",
        required=False,
        help="PIN numérico para acceso al portal (3-10 dígitos)"
    )

    _sql_constraints = [
        ('pin_unique', 'unique(pin)', 'El PIN debe ser único para cada empleado.'),
    ]

    @api.constrains('pin')
    def _check_pin_format(self):
        for employee in self:
            if employee.pin:
                # Remover espacios
                pin_clean = employee.pin.strip()
                if len(pin_clean) < 3:
                    raise ValidationError("El PIN debe tener al menos 3 dígitos.")
                if len(pin_clean) > 10:
                    raise ValidationError("El PIN no puede tener más de 10 dígitos.")
                # Solo permitir números
                if not pin_clean.isdigit():
                    raise ValidationError("El PIN debe ser numérico.")

    @api.model
    def create(self, vals):
        """Limpiar PIN al crear empleado"""
        if 'pin' in vals and vals['pin']:
            vals['pin'] = vals['pin'].strip()
        return super().create(vals)

    def write(self, vals):
        """Limpiar PIN al actualizar empleado"""
        if 'pin' in vals and vals['pin']:
            vals['pin'] = vals['pin'].strip()
        return super().write(vals)
