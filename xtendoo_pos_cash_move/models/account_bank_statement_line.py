from odoo import models, fields, api

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    move_type_display = fields.Selection(
        selection=[('in', 'Entrada'), ('out', 'Salida')],
        string='Tipo',
        compute='_compute_move_type_display',
        store=True,
    )

    @api.depends('amount')
    def _compute_move_type_display(self):
        for line in self:
            if line.amount >= 0:
                line.move_type_display = 'in'
            else:
                line.move_type_display = 'out'

