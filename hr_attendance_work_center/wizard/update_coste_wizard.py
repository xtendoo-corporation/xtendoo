from odoo import models, fields, api, _

class UpdateCosteWizard(models.TransientModel):
    _name = 'update.coste.wizard'
    _description = 'Resumen actualización de coste en asistencias'

    updated_count = fields.Integer('Registros actualizados')
    employee_names = fields.Text('Empleados con coste 0 tras actualizar')

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}

