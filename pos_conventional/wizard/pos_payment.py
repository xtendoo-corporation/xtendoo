# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosMakePaymentConventional(models.TransientModel):
    _inherit = "pos.make.payment"

    amount_received = fields.Float(
        string="Importe recibido",
        digits=0,
        help="Importe recibido del cliente (solo para efectivo)",
    )
    amount_change = fields.Float(
        string="Cambio",
        digits=0,
        compute="_compute_amount_change",
        store=False,
        help="Cambio a devolver al cliente",
    )
    is_cash_payment = fields.Boolean(
        string="Es pago en efectivo", compute="_compute_is_cash_payment", store=False
    )

    @api.depends("payment_method_id")
    def _compute_is_cash_payment(self):
        for record in self:
            record.is_cash_payment = (
                record.payment_method_id.is_cash_count
                if record.payment_method_id
                else False
            )

    @api.depends("amount_received", "amount", "is_cash_payment")
    def _compute_amount_change(self):
        for record in self:
            if record.is_cash_payment and record.amount_received > 0:
                record.amount_change = record.amount_received - record.amount
            else:
                record.amount_change = 0.0

    @api.onchange("payment_method_id")
    def _onchange_payment_method_id(self):
        """Resetear el importe recibido cuando cambia el método de pago"""
        if not self.is_cash_payment:
            self.amount_received = 0.0
        else:
            # Para efectivo, por defecto poner el importe exacto
            self.amount_received = self.amount

    def check(self, payment_method_id=None):
        """
        Permite forzar el método de pago si se pasa como argumento.
        """
        self.ensure_one()

        order = self.env["pos.order"].browse(self.env.context.get("active_id", False))

        # Si se pasa un payment_method_id, lo asignamos
        if payment_method_id:
            self.payment_method_id = payment_method_id

        # Validación original de split_transactions
        if self.payment_method_id.split_transactions and not order.partner_id:
            raise UserError(
                _(
                    "Customer is required for %s payment method.",
                    self.payment_method_id.name,
                )
            )

        currency = order.currency_id
        is_conventional = order.config_id and order.config_id.pos_non_touch
        init_data = self.read()[0]
        payment_method = self.env["pos.payment.method"].browse(
            init_data["payment_method_id"][0]
        )

        if not float_is_zero(init_data["amount"], precision_rounding=currency.rounding):
            order.add_payment(
                {
                    "pos_order_id": order.id,
                    "amount": order._get_rounded_amount(
                        init_data["amount"],
                        payment_method.is_cash_count
                        or not self.config_id.only_round_cash_method,
                    ),
                    "name": init_data["payment_name"],
                    "payment_method_id": init_data["payment_method_id"][0],
                }
            )

        if order.state == "draft" and order._is_pos_order_paid():
            _logger.info("Pedido %s está pagado, procesando...", order.name)
            order._process_saved_order(False)
            if order.state in {"paid", "done"}:
                _logger.info(
                    "Pedido %s ahora está en estado %s", order.name, order.state
                )
                order._send_order()
                order.config_id.notify_synchronisation(
                    order.config_id.current_session_id.id, 0
                )

            if (
                is_conventional
                and order.state in {"paid", "done"}
                and not order.account_move
            ):
                _logger.info(
                    "Ejecutando facturación automática para pedido %s", order.name
                )
                try:
                    result = order.action_validate_and_invoice()
                    if result and isinstance(result, dict) and result.get("type"):
                        # Si es una acción de impresión (client), verificar next_action
                        if result.get("type") == "ir.actions.client":
                            params = result.get("params", {})
                            # SOLO si no viene ya con una next_action específica (ej. Force Login)
                            if not params.get("next_action"):
                                result.setdefault("params", {})["next_action"] = {
                                    "type": "ir.actions.client",
                                    "tag": "pos_conventional_new_order",
                                    "params": {
                                        "config_id": order.config_id.id,
                                        "session_id": order.config_id.current_session_id.id,
                                    },
                                }
                        # Retornar la acción (sea print, o sea wizard de PIN)
                        return result
                except Exception as e:
                    _logger.exception(
                        "Error al facturar automáticamente el pedido %s: %s",
                        order.name,
                        str(e),
                    )
                    # Continuar con el flujo normal si falla la facturación

            # Redirigir automáticamente a un nuevo pedido usando una acción de cliente
            # SOLO si no se ejecutó la facturación automática arriba
            elif is_conventional and order.state in {"paid", "done"}:
                return {
                    "type": "ir.actions.client",
                    "tag": "pos_conventional_new_order",
                    "params": {
                        "config_id": order.config_id.id,
                        "session_id": order.config_id.current_session_id.id,
                    },
                }

            return {"type": "ir.actions.act_window_close"}

        return self.launch_payment()

    def action_pay_cash(self):
        cash_method = self.env["pos.payment.method"].search(
            [("is_cash_count", "=", True)], limit=1
        )
        if not cash_method:
            raise UserError(_("No se encontró método de pago en efectivo."))
        return self.check(payment_method_id=cash_method.id)

    def action_pay_card(self):
        # Cambia 'tarjeta' por el nombre exacto si es diferente
        card_method = self.env["pos.payment.method"].search(
            [("name", "ilike", "tarjeta")], limit=1
        )
        if not card_method:
            raise UserError(_("No se encontró método de pago con tarjeta."))
        return self.check(payment_method_id=card_method.id)

    def action_pay_account(self):
        account_method = self.env["pos.payment.method"].search(
            [("name", "ilike", "cuenta")], limit=1
        )
        if not account_method:
            raise UserError(_("No se encontró un método de pago tipo Cuenta."))
        return self.check(payment_method_id=account_method.id)