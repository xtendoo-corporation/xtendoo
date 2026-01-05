from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSessionCashMoveWizard(models.TransientModel):
    _name = 'pos.session.cash_move.wizard'
    _inherit = 'cashbox.calculator.mixin'
    _description = 'Wizard para Entrada/Salida de efectivo (backend)'

    session_id = fields.Many2one('pos.session', string='Session', required=True)
    type = fields.Selection([('in', 'Entrada de efectivo'), ('out', 'Salida de efectivo')], string='Tipo', default='out')
    amount = fields.Monetary(string='Importe', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='session_id.currency_id', readonly=True)
    reason = fields.Text(string='Razón')
    partner_id = fields.Many2one('res.partner', string='Partner')

    # Total calculado (usa el mixin)
    total_cashbox = fields.Monetary(
        string='Total calculado',
        compute='_compute_total_cashbox',
        store=True,
    )

    @api.depends('qty_500', 'qty_200', 'qty_100', 'qty_50', 'qty_20', 'qty_10', 'qty_5',
                 'qty_2', 'qty_1', 'qty_050', 'qty_020', 'qty_010', 'qty_005', 'qty_002', 'qty_001')
    def _compute_total_cashbox(self):
        for wizard in self:
            wizard.total_cashbox = wizard._calculate_cashbox_total()

    def action_confirm(self):
        self.ensure_one()

        # Determinar el importe a usar
        if self.use_cashbox:
            amount_to_use = self.total_cashbox
        else:
            amount_to_use = self.amount

        if not amount_to_use or amount_to_use <= 0:
            raise UserError(_('El importe debe ser mayor que 0.'))

        # Llamar al método existente try_cash_in_out en pos.session
        extras = {'translatedType': _('Entrada') if self.type == 'in' else _('Salida')}
        self.session_id.sudo().try_cash_in_out(
            self.type,
            amount_to_use,
            (self.reason or '').strip(),
            self.partner_id.id if self.partner_id else False,
            extras
        )
        return {'type': 'ir.actions.act_window_close'}



