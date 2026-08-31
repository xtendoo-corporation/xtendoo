from odoo import fields, models
from odoo.exceptions import UserError


class XtdPaymentOrderLine(models.Model):
    _name = "xtd.payment.order.line"
    _description = "Líneas importadas de la remesa Xtendoo"

    order_id = fields.Many2one("account.payment.order", string="Remesa", ondelete="cascade")
    source_type = fields.Selection(
        selection=[("payment", "Pago"), ("move_line", "Apunte")],
        string="Origen",
        default="payment",
        required=True,
        readonly=True,
    )
    payment_id = fields.Many2one("account.payment", string="Pago")
    move_line_id = fields.Many2one("account.move.line", string="Apunte contable")
    name = fields.Char(string="Referencia")
    partner_id = fields.Many2one("res.partner", string="Cliente")
    date = fields.Date(string="Fecha")
    due_date = fields.Date(string="Vencimiento")
    amount = fields.Monetary(string="Importe")
    currency_id = fields.Many2one("res.currency", string="Moneda")
    note = fields.Text(string="Nota")



class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    xtd_accounting_line_ids = fields.One2many(
        "xtd.payment.order.line", "order_id", string="Apuntes contables"
    )
    xtd_source_type = fields.Selection(
        selection=[
            ("oca", "Pending Transactions"),
            ("existing_payments", "Existing Payments"),
        ],
        string="Source Type",
        default="oca",
        required=True,
        copy=False,
        tracking=True,
    )

    def _xtd_existing_payments_orders(self):
        return self.filtered(lambda order: order.xtd_source_type == "existing_payments")

    def xtd_create_from_existing_payments(self, payments, lot_date):
        self.ensure_one()
        payments._xtd_validate_for_effect_lot()
        if self.xtd_source_type != "existing_payments":
            raise UserError(
                self.env._(
                    "This payment/debit order is not configured for existing payments."
                )
            )
        if self.state != "draft":
            raise UserError(
                self.env._(
                    "Only draft payment/debit orders can receive existing payments."
                )
            )
        if self.payment_ids or self.payment_lot_ids:
            raise UserError(
                self.env._(
                    "This payment/debit order already contains payments or lots."
                )
            )
        lot = self.env["account.payment.lot"].create(
            {
                "order_id": self.id,
                "currency_id": payments[0].currency_id.id,
                "date": lot_date,
                "name": f"{self.name}/LOT1",
            }
        )
        payments.write(
            {
                "payment_order_id": self.id,
                "payment_lot_id": lot.id,
            }
        )
        self.write(
            {
                "state": "uploaded",
                "date_generated": False,
                "date_uploaded": lot_date,
            }
        )
        return lot

    def cancel2draft(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).cancel2draft() if regular_orders else True
        for order in xtd_orders:
            if order.payment_ids.filtered("is_matched"):
                raise UserError(
                    self.env._(
                        "You cannot reset this lot because it contains payments already "
                        "matched with bank transactions."
                    )
                )
            if order.payment_file_id:
                order.payment_file_id.unlink()
            order.payment_ids.write(
                {
                    "payment_lot_id": False,
                    "payment_order_id": False,
                }
            )
            order.payment_lot_ids.unlink()
            order.write(
                {
                    "state": "draft",
                    "date_generated": False,
                    "date_uploaded": False,
                    "payment_file_id": False,
                }
            )
        return result

    def action_cancel(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).action_cancel() if regular_orders else True
        for order in xtd_orders:
            if order.payment_ids.filtered("is_matched"):
                raise UserError(
                    self.env._(
                        "You cannot cancel this lot because it contains payments already "
                        "matched with bank transactions."
                    )
                )
            if order.payment_file_id:
                order.payment_file_id.unlink()
            order.payment_ids.write(
                {
                    "payment_lot_id": False,
                    "payment_order_id": False,
                }
            )
            order.payment_lot_ids.unlink()
            order.write(
                {
                    "state": "cancel",
                    "date_generated": False,
                    "payment_file_id": False,
                }
            )
        return result

    def draft2open(self):
        xtd_orders = self._xtd_existing_payments_orders()
        if xtd_orders:
            raise UserError(
                self.env._(
                    "Orders created from existing payments must be generated from the "
                    "deposit/remittance wizard."
                )
            )
        return super().draft2open()

    def open2generated(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).open2generated() if regular_orders else {}
        if xtd_orders:
            raise UserError(
                self.env._(
                    "File generation is not available for payment/debit orders built "
                    "from existing payments."
                )
            )
        return result

    def generated2uploaded(self):
        xtd_orders = self._xtd_existing_payments_orders()
        regular_orders = self - xtd_orders
        result = super(AccountPaymentOrder, regular_orders).generated2uploaded() if regular_orders else True
        for order in xtd_orders:
            order.write(
                {
                    "state": "uploaded",
                    "date_uploaded": fields.Date.context_today(order),
                }
            )
        return result

    def _xtd_get_candidate_move_lines(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        method_line = self.payment_method_line_id
        domain = [
            ("reconciled", "=", False),
            ("company_id", "=", self.company_id.id),
            ("move_id.payment_state", "in", ("not_paid", "partial")),
            ("debit", ">", 0),
            (
                "account_id.account_type",
                "in",
                ["asset_receivable", "liability_payable"],
            ),
        ]
        if method_line.default_journal_ids:
            domain.append(("journal_id", "in", method_line.default_journal_ids.ids))
        if method_line.default_target_move == "posted":
            domain.append(("move_id.state", "=", "posted"))
        else:
            domain.append(("move_id.state", "in", ("draft", "posted")))
        if method_line.default_date_type == "move":
            domain.append(("date", "<=", today))
        else:
            domain += [
                "|",
                ("date_maturity", "<=", today),
                ("date_maturity", "=", False),
            ]
        if method_line.default_invoice:
            domain.append(
                (
                    "move_id.move_type",
                    "in",
                    ("in_invoice", "out_invoice", "in_refund", "out_refund"),
                )
            )
        if method_line.default_payment_mode == "same":
            domain.append(
                (
                    "move_id.preferred_payment_method_line_id",
                    "=",
                    method_line.id,
                )
            )
        elif method_line.default_payment_mode == "same_or_null":
            domain += [
                "|",
                ("move_id.preferred_payment_method_line_id", "=", False),
                ("move_id.preferred_payment_method_line_id", "=", method_line.id),
            ]
        paylines = self.env["account.payment.line"].search(
            [
                ("state", "in", ("draft", "open", "generated")),
                ("move_line_id", "!=", False),
            ]
        )
        if paylines:
            domain.append(("id", "not in", paylines.mapped("move_line_id").ids))
        return self.env["account.move.line"].search(domain, order="date_maturity, date, id")

    def action_import_accounting_entries(self):
        """Importar líneas contables asociadas a esta remesa a la pestaña interna.

        Prioridad:
        1) pagos ya vinculados a la orden/lotes,
        2) si no existen, apuntes contables candidatos usando la misma lógica
           funcional del asistente original de OCA para vencimiento de hoy.
        """
        Payment = self.env["account.payment"]
        Line = self.env["xtd.payment.order.line"]
        for order in self:
            today = fields.Date.context_today(order)
            # obtener pagos directamente vinculados a la orden o al lote
            payments = order.payment_ids
            if not payments and order.payment_lot_ids:
                payments = Payment.search([("payment_lot_id", "in", order.payment_lot_ids.ids)])
            # fallback: si no hay pagos vinculados, buscar automáticamente
            # efectos/apuntes originales OCA: se buscan en account.move.line,
            # no en account.payment. Por eso el botón original sí encuentra.
            move_lines = self.env["account.move.line"]
            if not payments:
                move_lines = order._xtd_get_candidate_move_lines()
            if not payments and not move_lines:
                pending_domain = [
                    ("reconciled", "=", False),
                    ("company_id", "=", order.company_id.id),
                    ("move_id.payment_state", "in", ("not_paid", "partial")),
                    ("debit", ">", 0),
                    (
                        "account_id.account_type",
                        "in",
                        ["asset_receivable", "liability_payable"],
                    ),
                ]
                if order.payment_method_line_id.default_journal_ids:
                    pending_domain.append(
                        (
                            "journal_id",
                            "in",
                            order.payment_method_line_id.default_journal_ids.ids,
                        )
                    )
                if order.payment_method_line_id.default_target_move == "posted":
                    pending_domain.append(("move_id.state", "=", "posted"))
                else:
                    pending_domain.append(("move_id.state", "in", ("draft", "posted")))
                if order.payment_method_line_id.default_date_type == "move":
                    pending_domain.append(("date", "<=", today))
                else:
                    pending_domain += [
                        "|",
                        ("date_maturity", "<=", today),
                        ("date_maturity", "=", False),
                    ]
                if order.payment_method_line_id.default_invoice:
                    pending_domain.append(
                        (
                            "move_id.move_type",
                            "in",
                            ("in_invoice", "out_invoice", "in_refund", "out_refund"),
                        )
                    )
                if order.payment_method_line_id.default_payment_mode == "same":
                    pending_domain.append(
                        (
                            "move_id.preferred_payment_method_line_id",
                            "=",
                            order.payment_method_line_id.id,
                        )
                    )
                elif order.payment_method_line_id.default_payment_mode == "same_or_null":
                    pending_domain += [
                        "|",
                        ("move_id.preferred_payment_method_line_id", "=", False),
                        (
                            "move_id.preferred_payment_method_line_id",
                            "=",
                            order.payment_method_line_id.id,
                        ),
                    ]
                other_due_move_lines = self.env["account.move.line"].search(
                    pending_domain,
                    order="date_maturity, date, id",
                    limit=5,
                )
                today_scope_count = self.env["account.move.line"].search_count(
                    pending_domain + [("date_maturity", "=", today)]
                )
                total_scope_count = self.env["account.move.line"].search_count(pending_domain)
                info_lines = [
                    self.env._("No se han encontrado apuntes/efectos con fecha de vencimiento de hoy para importar."),
                    self.env._("Fecha buscada: %s") % fields.Date.to_string(today),
                    self.env._("Compañía: %s") % (order.company_id.display_name or "-"),
                    self.env._("Diario bancario de la remesa: %s") % (order.journal_id.display_name or "-"),
                    self.env._("Método de pago: %s") % (order.payment_method_line_id.display_name or "-"),
                    self.env._("Diarios contables usados por el filtro OCA: %s")
                    % (", ".join(order.payment_method_line_id.default_journal_ids.mapped("display_name")) or "-"),
                    self.env._("Apuntes pendientes con vencimiento hoy en el ámbito OCA: %s") % today_scope_count,
                    self.env._("Apuntes pendientes totales en el ámbito OCA: %s") % total_scope_count,
                ]
                if other_due_move_lines:
                    info_lines.append("")
                    info_lines.append(self.env._("Primeros apuntes pendientes encontrados con otros vencimientos:"))
                    for line in other_due_move_lines:
                        due_date = line.date_maturity and fields.Date.to_string(line.date_maturity) or self.env._("Sin vencimiento")
                        reference = line.move_id.name or line.name or self.env._("Apunte %s") % line.id
                        partner = line.partner_id.display_name or "-"
                        amount_value = line.amount_residual_currency if line.currency_id else line.amount_residual
                        amount = f"{amount_value:.2f}"
                        currency = (line.currency_id or line.company_id.currency_id).name or ""
                        info_lines.append(
                            f"- {reference} | {partner} | {due_date} | {amount} {currency}".strip()
                        )
                raise UserError(
                    "\n".join(info_lines)
                )
            created = 0
            for pay in payments:
                # evitar duplicados por payment_id
                if Line.search([("order_id", "=", order.id), ("payment_id", "=", pay.id)], limit=1):
                    continue
                vals = {
                    "order_id": order.id,
                    "payment_id": pay.id,
                    "name": pay.payment_reference or pay.name or "Pago",
                    "partner_id": pay.partner_id.id,
                    "date": pay.payment_date or pay.date,
                    "amount": pay.amount,
                    "currency_id": pay.currency_id and pay.currency_id.id or order.company_id.currency_id.id,
                    "note": pay.communication or "",
                }
                Line.create(vals)
                created += 1
            for move_line in move_lines:
                if Line.search([("order_id", "=", order.id), ("move_line_id", "=", move_line.id)], limit=1):
                    continue
                amount_value = move_line.amount_residual_currency if move_line.currency_id else move_line.amount_residual
                vals = {
                    "order_id": order.id,
                    "source_type": "move_line",
                    "move_line_id": move_line.id,
                    "name": move_line.move_id.name or move_line.name or "Apunte",
                    "partner_id": move_line.partner_id.id,
                    "date": move_line.date,
                    "due_date": move_line.date_maturity,
                    "amount": amount_value,
                    "currency_id": (move_line.currency_id or move_line.company_id.currency_id).id,
                    "note": move_line.move_id.ref or move_line.name or "",
                }
                Line.create(vals)
                created += 1
            if created == 0:
                raise UserError(self.env._("No se han importado nuevas líneas (posiblemente ya existan)."))
        return True

