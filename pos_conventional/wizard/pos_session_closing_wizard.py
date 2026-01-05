from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSessionClosingWizard(models.TransientModel):
    _name = 'pos.session.closing.wizard'
    _inherit = 'cashbox.calculator.mixin'
    _description = 'Wizard para cierre de sesión POS no táctil'

    session_id = fields.Many2one('pos.session', string='Sesión', required=True, readonly=True)
    cash_register_balance_end_real = fields.Monetary(
        string='Dinero contado en caja',
        currency_field='currency_id',
        help='Cantidad total de dinero en efectivo contado al cerrar la caja',
        compute='_compute_cash_balance_end_real',
        store=True,
        readonly=False
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

    @api.depends('session_id')
    def _compute_session_totals(self):
        for wizard in self:
            cash_total = 0.0
            card_total = 0.0
            other_total = 0.0

            # Agrupar pagos por tipo de método
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
                    # Otros métodos de pago
                    other_total += amount

            wizard.cash_payments = cash_total
            wizard.card_payments = card_total
            wizard.other_payments = other_total
            wizard.total_payments = cash_total + card_total + other_total

            # Total de entradas y salidas de efectivo
            wizard.cash_in_out_total = wizard.session_id.cash_real_transaction

    @api.depends('qty_500', 'qty_200', 'qty_100', 'qty_50', 'qty_20', 'qty_10', 'qty_5',
                 'qty_2', 'qty_1', 'qty_050', 'qty_020', 'qty_010', 'qty_005', 'qty_002', 'qty_001',
                 'use_cashbox')
    def _compute_cash_balance_end_real(self):
        for wizard in self:
            if wizard.use_cashbox:
                wizard.cash_register_balance_end_real = wizard._calculate_cashbox_total()

    @api.depends('cash_register_balance_end_real', 'cash_register_balance_end')
    def _compute_difference(self):
        for wizard in self:
            wizard.cash_register_difference = wizard.cash_register_balance_end_real - wizard.cash_register_balance_end

    def action_close_session(self):
        """
        Cierra la sesión POS usando los métodos estándares de Odoo.
        Reutiliza completamente la lógica del core.
        """
        self.ensure_one()

        # Validar que la sesión esté en estado abierto
        if self.session_id.state not in ['opened', 'closing_control']:
            raise UserError(_(
                'Solo puedes cerrar sesiones en estado abierto o en proceso de cierre.'
            ))

        # Si hay control de efectivo, guardar el dinero contado
        if self.session_id.cash_control:
            # Usar el método estándar de Odoo para registrar el efectivo contado
            result = self.session_id.post_closing_cash_details(self.cash_register_balance_end_real)
            if not result.get('successful'):
                raise UserError(result.get('message', _('Error al registrar el efectivo.')))

        # Guardar la nota de cierre si existe
        if self.closing_note:
            self.session_id.message_post(
                body=_('Motivo de cierre: %s') % self.closing_note,
                subject=_('Nota de cierre de sesión')
            )

        # Llamar al método estándar de cierre de sesión
        # Este método hace toda la lógica: asientos contables, validaciones, etc.
        try:
            result = self.session_id.action_pos_session_closing_control()

            # Si el resultado es un diccionario, puede ser un wizard de desbalance
            if isinstance(result, dict):
                # Retornar el wizard de desbalance si es necesario
                return result

        except UserError as e:
            raise UserError(_(
                'Error al cerrar la sesión: %s'
            ) % str(e))

        # Retornar a la vista kanban de configuraciones POS
        return {
            'type': 'ir.actions.act_window',
            'name': _('Punto de Venta'),
            'res_model': 'pos.config',
            'view_mode': 'kanban,form',
            'target': 'main',
            'domain': [],
            'context': {
                'search_default_group_by_company': True,
            },
        }



