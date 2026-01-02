from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSessionCashMoveWizard(models.TransientModel):
    _name = 'pos.session.cash_move.wizard'
    _description = 'Wizard para Entrada/Salida de efectivo (backend)'

    session_id = fields.Many2one('pos.session', string='Session', required=True)
    type = fields.Selection([('in', 'Entrada de efectivo'), ('out', 'Salida de efectivo')], string='Tipo', default='out')
    amount = fields.Monetary(string='Importe', required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='session_id.currency_id', readonly=True)
    reason = fields.Text(string='Razón')
    partner_id = fields.Many2one('res.partner', string='Partner')

    def action_confirm(self):
        self.ensure_one()
        if not self.amount or self.amount <= 0:
            raise UserError(_('El importe debe ser mayor que 0.'))
        # Llamar al método existente try_cash_in_out en pos.session
        extras = {'translatedType': _('Entrada') if self.type == 'in' else _('Salida')}
        # Use sudo to avoid permission issues for cash creation through UI (keeps original permission checks inside try_cash_in_out)
        self.session_id.sudo().try_cash_in_out(self.type, self.amount, (self.reason or '').strip(), self.partner_id.id if self.partner_id else False, extras)
        return {'type': 'ir.actions.act_window_close'}
