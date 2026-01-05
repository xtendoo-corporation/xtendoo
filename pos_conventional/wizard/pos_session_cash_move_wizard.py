from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSessionCashMoveWizard(models.TransientModel):
    _name = 'pos.session.cash_move.wizard'
    _description = 'Wizard para Entrada/Salida de efectivo (backend)'

    session_id = fields.Many2one('pos.session', string='Session', required=True)
    type = fields.Selection([('in', 'Entrada de efectivo'), ('out', 'Salida de efectivo')], string='Tipo', default='out')
    amount = fields.Monetary(string='Importe', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='session_id.currency_id', readonly=True)
    reason = fields.Text(string='Razón')
    partner_id = fields.Many2one('res.partner', string='Partner')

    # Toggle para usar calculadora
    use_cashbox = fields.Boolean(string='Usar calculadora de efectivo', default=False)

    # Campos para billetes
    qty_500 = fields.Integer(string='500 €', default=0)
    qty_200 = fields.Integer(string='200 €', default=0)
    qty_100 = fields.Integer(string='100 €', default=0)
    qty_50 = fields.Integer(string='50 €', default=0)
    qty_20 = fields.Integer(string='20 €', default=0)
    qty_10 = fields.Integer(string='10 €', default=0)
    qty_5 = fields.Integer(string='5 €', default=0)

    # Campos para monedas
    qty_2 = fields.Integer(string='2 €', default=0)
    qty_1 = fields.Integer(string='1 €', default=0)
    qty_050 = fields.Integer(string='0,50 €', default=0)
    qty_020 = fields.Integer(string='0,20 €', default=0)
    qty_010 = fields.Integer(string='0,10 €', default=0)
    qty_005 = fields.Integer(string='0,05 €', default=0)
    qty_002 = fields.Integer(string='0,02 €', default=0)
    qty_001 = fields.Integer(string='0,01 €', default=0)

    # Total calculado
    total_cashbox = fields.Monetary(
        string='Total calculado',
        compute='_compute_total_cashbox',
        store=True,
    )

    @api.depends('qty_500', 'qty_200', 'qty_100', 'qty_50', 'qty_20', 'qty_10', 'qty_5',
                 'qty_2', 'qty_1', 'qty_050', 'qty_020', 'qty_010', 'qty_005', 'qty_002', 'qty_001')
    def _compute_total_cashbox(self):
        for wizard in self:
            wizard.total_cashbox = (
                wizard.qty_500 * 500 +
                wizard.qty_200 * 200 +
                wizard.qty_100 * 100 +
                wizard.qty_50 * 50 +
                wizard.qty_20 * 20 +
                wizard.qty_10 * 10 +
                wizard.qty_5 * 5 +
                wizard.qty_2 * 2 +
                wizard.qty_1 * 1 +
                wizard.qty_050 * 0.50 +
                wizard.qty_020 * 0.20 +
                wizard.qty_010 * 0.10 +
                wizard.qty_005 * 0.05 +
                wizard.qty_002 * 0.02 +
                wizard.qty_001 * 0.01
            )

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



