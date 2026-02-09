from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class PosSessionClosingWizard(models.TransientModel):
    _name = "pos.session.closing.wizard"
    _description = "Wizard para cierre de sesión POS no táctil"

    session_id = fields.Many2one(
        "pos.session", string="Sesión", required=True, readonly=True
    )
    cash_register_balance_end_real = fields.Float(
        string="Recuento de efectivo",
        help="Cantidad total de dinero en efectivo contado al cerrar la caja",
        default=0.0,
    )
    card_number = fields.Monetary(
        string="Tarjeta número",
        currency_field="currency_id",
        default=lambda self: self._default_card_amount(),
        help="Importe contado/introducido para pagos con tarjeta (referencia).",
    )
    currency_id = fields.Many2one(
        "res.currency", related="session_id.currency_id", readonly=True
    )
    cash_control = fields.Boolean(related="session_id.cash_control", readonly=True)
    cash_register_balance_start = fields.Monetary(
        string="Dinero inicial",
        related="session_id.cash_register_balance_start",
        readonly=True,
    )
    cash_register_balance_end = fields.Monetary(
        string="Dinero teórico",
        related="session_id.cash_register_balance_end",
        readonly=True,
        help="Dinero inicial + ventas en efectivo - devoluciones",
    )
    cash_register_difference = fields.Monetary(
        string="Diferencia",
        compute="_compute_difference",
        store=True,
        help="Diferencia entre dinero contado y dinero teórico",
    )
    closing_note = fields.Text(
        string="Motivo del cierre",
        help="Nota opcional explicando el motivo del cierre de la sesión",
    )
    state = fields.Selection(
        [("input", "Entrada"), ("confirmation", "Confirmación")],
        default="input",
        string="Estado",
    )

    # Campos para mostrar resumen de la sesión
    total_payments = fields.Monetary(
        string="Total de pagos", compute="_compute_session_totals", readonly=True
    )
    cash_payments = fields.Monetary(
        string="Pagos en efectivo", compute="_compute_session_totals", readonly=True
    )
    card_payments = fields.Monetary(
        string="Pagos con tarjeta", compute="_compute_session_totals", readonly=True
    )
    other_payments = fields.Monetary(
        string="Otros pagos", compute="_compute_session_totals", readonly=True
    )
    cash_in_out_total = fields.Monetary(
        string="Entradas/Salidas de efectivo",
        compute="_compute_session_totals",
        readonly=True,
    )
    cash_in_out_line_ids = fields.Many2many(
        comodel_name="account.bank.statement.line",
        compute="_compute_cash_in_out_lines",
        string="Movimientos de caja",
        readonly=True,
    )

    # Campos para "Cuenta Cliente" (pedidos vinculados a sale.order)
    linked_sale_orders_total = fields.Monetary(
        string="Total Cuenta Cliente",
        compute="_compute_session_totals",
        readonly=True,
        help="Total de pedidos POS vinculados a pedidos de venta tradicionales",
    )
    linked_sale_orders_count = fields.Integer(
        string="Pedidos a Cuenta",
        compute="_compute_session_totals",
        readonly=True,
        help="Número de pedidos POS vinculados a pedidos de venta tradicionales",
    )

    @api.depends("session_id")
    def _compute_session_totals(self):
        for wizard in self:
            cash_total = 0.0
            card_total = 0.0
            other_total = 0.0

            for payment in wizard.session_id.order_ids.mapped("payment_ids"):
                method = payment.payment_method_id
                amount = payment.amount

                if method.is_cash_count:
                    # Método de pago en efectivo
                    cash_total += amount
                elif method.type in ["bank", "pay_later"]:
                    # Método de pago con tarjeta/banco
                    card_total += amount
                else:
                    other_total += amount

            wizard.cash_payments = cash_total
            wizard.card_payments = card_total
            wizard.other_payments = other_total
            wizard.total_payments = cash_total + card_total + other_total

            # Entradas/Salidas de efectivo: sumar líneas de caja vinculadas a la sesión.
            # En el core de Odoo, `cash_real_transaction` solo se actualiza al validar/cerrar.
            wizard.cash_in_out_total = sum(wizard.session_id.statement_line_ids.mapped('amount'))

            linked_orders = wizard.session_id.order_ids.filtered(
                lambda o: o.linked_sale_order_id
            )
            wizard.linked_sale_orders_count = len(linked_orders)
            wizard.linked_sale_orders_total = sum(
                order.amount_total for order in linked_orders
            )

    @api.depends("cash_register_balance_end_real", "cash_register_balance_end")
    def _compute_difference(self):
        for wizard in self:
            wizard.cash_register_difference = (
                wizard.cash_register_balance_end_real - wizard.cash_register_balance_end
            )

    @api.depends("session_id")
    def _compute_cash_in_out_lines(self):
        for wizard in self:
            lines = wizard.session_id.statement_line_ids.sorted(lambda l: (l.date or fields.Date.today(), l.id))
            wizard.cash_in_out_line_ids = [(6, 0, lines.ids)]

    def action_close_session(self):
        """
        Cierra la sesión POS usando los métodos estándares de Odoo.
        Reutiliza completamente la lógica del core.
        """
        self.ensure_one()

        # Validar que la sesión esté en estado abierto
        if self.session_id.state not in ["opened", "closing_control"]:
            raise UserError(
                _(
                    "Solo puedes cerrar sesiones en estado abierto o en proceso de cierre."
                )
            )

        # Si hay control de efectivo, guardar el dinero contado
        if self.session_id.cash_control:
            # Usar el método estándar de Odoo para registrar el efectivo contado
            result = self.session_id.post_closing_cash_details(
                self.cash_register_balance_end_real
            )
            if not result.get("successful"):
                raise UserError(
                    result.get("message", _("Error al registrar el efectivo."))
                )

        if not self.session_id.stop_at:
            self.session_id.write({"stop_at": fields.Datetime.now()})

        difference = (
            self.cash_register_balance_end_real
            - self.session_id.cash_register_balance_end
        )
        currency = self.currency_id

        if not float_is_zero(difference, precision_rounding=currency.rounding):
            # Si estamos en estado 'input', pasamos a confirmación y recargamos la vista
            if self.state == "input":
                self.write({"state": "confirmation"})
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "pos.session.closing.wizard",
                    "view_mode": "form",
                    "res_id": self.id,
                    "target": "new",
                }

        # Llamar al método estándar de cierre de sesión
        try:
            result = self.session_id.action_pos_session_closing_control()

            # Si el resultado es un diccionario, puede ser un wizard de desbalance
            if isinstance(result, dict):
                return result
        except UserError as e:
            raise UserError(_("Error al cerrar la sesión: %s") % str(e))

        # Retornar a la vista kanban de configuraciones POS
        return {
            "type": "ir.actions.act_window",
            "name": _("Punto de Venta"),
            "res_model": "pos.config",
            "view_mode": "kanban,form",
            "target": "main",
            "domain": [],
            "context": {"search_default_group_by_company": True},
        }

    def action_print_daily_report(self):
        """
        Imprime el informe de ventas diarias (X report) de la sesión.
        Utiliza el mismo informe que genera Odoo en el POS.
        """
        self.ensure_one()
        # Usar el mismo método que el wizard de Odoo (pos.daily.sales.reports.wizard)
        data = {
            "date_start": False,
            "date_stop": False,
            "config_ids": self.session_id.config_id.ids,
            "session_ids": self.session_id.ids,
        }
        return self.env.ref("point_of_sale.sale_details_report").report_action(
            [], data=data
        )

    def action_open_cash_calculator(self):
        """
        Abre un wizard separado con la calculadora de monedas y billetes
        """
        self.ensure_one()

        # Crear el wizard de calculadora
        calculator_wizard = self.env["pos.cash.calculator.wizard"].create(
            {
                "closing_wizard_id": self.id,
                "currency_id": self.currency_id.id,
            }
        )

        return {
            "name": _("Monedas/billetes"),
            "type": "ir.actions.act_window",
            "res_model": "pos.cash.calculator.wizard",
            "view_mode": "form",
            "res_id": calculator_wizard.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_open_cash_move_wizard(self):
        """
        Abre el wizard de entrada/salida de efectivo sin cerrar el wizard de cierre.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Entrada/Salida de efectivo"),
            "res_model": "pos.session.cash_move.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.session_id.id,
            },
        }

    @api.model
    def _default_card_amount(self):
        session_id = self.env.context.get('default_session_id')
        if not session_id:
            return 0.0
        session = self.env['pos.session'].browse(session_id)
        if not session:
            return 0.0

        total = 0.0
        for payment in session.order_ids.mapped('payment_ids'):
            method = payment.payment_method_id
            if method and method.type in ['bank', 'pay_later']:
                total += payment.amount
        return total

