from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PosSessionPinWizard(models.TransientModel):
    _name = 'pos.session.pin.wizard'
    _description = 'Wizard para validar PIN de apertura POS'

    session_id = fields.Many2one('pos.session', required=True, readonly=True)
    user_id = fields.Many2one('res.users', required=True, readonly=True, default=lambda self: self.env.user)
    employee_pin = fields.Char(string='PIN del empleado')

    def action_validate_pin(self):
        self.ensure_one()
        # Validar el PIN usando la lógica del wizard original
        self.env['pos.session.opening.wizard']._validate_employee_pin({
            'session_id': self.session_id,
            'user_id': self.user_id,
            'employee_pin': self.employee_pin,
        })
        # Al validar, abrir el segundo wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.session.opening.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.session_id.id,
                'default_user_id': self.user_id.id,
            }
        }

