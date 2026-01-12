from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class PosSessionClosingWizard(models.TransientModel):
    _name = 'pos.session.closing.wizard'
    _description = 'Wizard para cierre de sesión POS no táctil'

    session_id = fields.Many2one('pos.session', string='Sesión', required=True, readonly=True)
    cash_register_balance_end_real = fields.Monetary(
        string='Dinero contado en caja',
        currency_field='currency_id',
        help='Cantidad total de dinero en efectivo contado al cerrar la caja',
        default=0.0
    )
    currency_id = fields.Many2one('res.currency', related='session_id.currency_id', readonly=True)
    cash_control = fields.Boolean(related='session_id.cash_control', readonly=True)
    cash_register_balance_start = fields.Monetary(
        string='Dinero inicial',
        related='session_id.cash_register_balance_start',
        readonly=True
    )
    cash_register_balance_end = fields.Monetary(
        string='Dinero teórico',
        related='session_id.cash_register_balance_end',
        readonly=True,
        help='Dinero inicial + ventas en efectivo - devoluciones'
    )
    cash_register_difference = fields.Monetary(
        string='Diferencia',
        compute='_compute_difference',
        store=True,
        help='Diferencia entre dinero contado y dinero teórico'
    )
    closing_note = fields.Text(
        string='Motivo del cierre',
        help='Nota opcional explicando el motivo del cierre de la sesión'
    )

    # Campos para mostrar resumen de la sesión
    total_payments = fields.Monetary(
        string='Total de pagos',
        compute='_compute_session_totals',
        readonly=True
    )
    cash_payments = fields.Monetary(
        string='Pagos en efectivo',
        compute='_compute_session_totals',
        readonly=True
    )
    card_payments = fields.Monetary(
        string='Pagos con tarjeta',
        compute='_compute_session_totals',
        readonly=True
    )
    other_payments = fields.Monetary(
        string='Otros pagos',
        compute='_compute_session_totals',
        readonly=True
    )
    cash_in_out_total = fields.Monetary(
        string='Entradas/Salidas de efectivo',
        compute='_compute_session_totals',
        readonly=True
    )

    # Campos para "Cuenta Cliente" (pedidos vinculados a sale.order)
    linked_sale_orders_total = fields.Monetary(
        string='Total Cuenta Cliente',
        compute='_compute_session_totals',
        readonly=True,
        help='Total de pedidos POS vinculados a pedidos de venta tradicionales'
    )
    linked_sale_orders_count = fields.Integer(
        string='Pedidos a Cuenta',
        compute='_compute_session_totals',
        readonly=True,
        help='Número de pedidos POS vinculados a pedidos de venta tradicionales'
    )

    @api.depends('session_id')
    def _compute_session_totals(self):
        for wizard in self:
            cash_total = 0.0
            card_total = 0.0
            other_total = 0.0


            for payment in wizard.session_id.order_ids.mapped('payment_ids'):
                method = payment.payment_method_id
                amount = payment.amount

                if method.is_cash_count:
                    # Método de pago en efectivo
                    cash_total += amount
                elif method.type in ['bank', 'pay_later']:
                    # Método de pago con tarjeta/banco
                    card_total += amount
                else:

                    other_total += amount

            wizard.cash_payments = cash_total
            wizard.card_payments = card_total
            wizard.other_payments = other_total
            wizard.total_payments = cash_total + card_total + other_total


            wizard.cash_in_out_total = wizard.session_id.cash_real_transaction


            linked_orders = wizard.session_id.order_ids.filtered(lambda o: o.linked_sale_order_id)
            wizard.linked_sale_orders_count = len(linked_orders)
            wizard.linked_sale_orders_total = sum(order.amount_total for order in linked_orders)

    @api.depends('cash_register_balance_end_real', 'cash_register_balance_end')
    def action_close_session(self):
        self.ensure_one()

        if self.session_id.state not in ['opened', 'closing_control']:
            raise UserError(_('Solo puedes cerrar sesiones en estado abierto o en proceso de cierre.'))

        if self.session_id.cash_control:
            self.session_id.post_closing_cash_details(self.cash_register_balance_end_real)

        if self.closing_note:
            self.session_id.message_post(body=_('Motivo de cierre: %s') % self.closing_note)

        difference = self.cash_register_balance_end_real - self.session_id.cash_register_balance_end
        currency = self.currency_id

        balancing_account = False
        amount_to_balance = 0.0

        if not float_is_zero(difference, precision_rounding=currency.rounding):
            cash_method = self.session_id.payment_method_ids.filtered(lambda pm: pm.is_cash_count)[:1]
            journal = cash_method.journal_id

            if journal:
                amount_to_balance = difference
                if difference > 0:
                    balancing_account = journal.profit_account_id or journal.default_account_id
                else:
                    balancing_account = journal.loss_account_id or journal.default_account_id

                if not balancing_account:
                    raise UserError(
                        _("El diario %s no tiene cuentas de pérdidas/ganancias configuradas.") % journal.name)

        self.session_id.action_pos_session_validate(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs={}
        )

        if self.session_id.state != 'closed':
            self.session_id.write({'state': 'closed', 'stop_at': fields.Datetime.now()})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Punto de Venta'),
            'res_model': 'pos.config',
            'view_mode': 'kanban,form',
            'target': 'main',
            'domain': [],
            'context': {'search_default_group_by_company': True},
        }

    def action_print_daily_report(self):
        """
        Imprime el informe de ventas diarias (X report) de la sesión.
        Utiliza el mismo informe que genera Odoo en el POS.
        """
        self.ensure_one()
        # Usar el mismo método que el wizard de Odoo (pos.daily.sales.reports.wizard)
        data = {
            'date_start': False,
            'date_stop': False,
            'config_ids': self.session_id.config_id.ids,
            'session_ids': self.session_id.ids
        }
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)

    def action_open_cash_calculator(self):
        """
        Abre un wizard separado con la calculadora de monedas y billetes
        """
        self.ensure_one()

        # Crear el wizard de calculadora
        calculator_wizard = self.env['pos.cash.calculator.wizard'].create({
            'closing_wizard_id': self.id,
            'currency_id': self.currency_id.id,
        })

        return {
            'name': _('Monedas/billetes'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.cash.calculator.wizard',
            'view_mode': 'form',
            'res_id': calculator_wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_open_cash_move_wizard(self):
        """
        Abre el wizard de entrada/salida de efectivo sin cerrar el wizard de cierre.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Entrada/Salida de efectivo'),
            'res_model': 'pos.session.cash_move.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.session_id.id,
            },
        }
