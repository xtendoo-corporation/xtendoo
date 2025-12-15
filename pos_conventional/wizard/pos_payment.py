# -*- coding: utf-8 -*-
import logging
from odoo import models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosMakePaymentConventional(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        """
        Override del método check para que después de registrar el pago,
        automáticamente valide y facture el pedido si está configurado
        como POS convencional (backend / no táctil).
        """
        self.ensure_one()

        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))

        # Validación original de split_transactions
        if self.payment_method_id.split_transactions and not order.partner_id:
            raise UserError(_(
                "Customer is required for %s payment method.",
                self.payment_method_id.name
            ))

        currency = order.currency_id

        # Verificar si es un POS convencional (backend / no táctil)
        is_conventional = order.config_id and order.config_id.pos_non_touch

        init_data = self.read()[0]
        payment_method = self.env['pos.payment.method'].browse(init_data['payment_method_id'][0])

        if not float_is_zero(init_data['amount'], precision_rounding=currency.rounding):
            order.add_payment({
                'pos_order_id': order.id,
                'amount': order._get_rounded_amount(
                    init_data['amount'],
                    payment_method.is_cash_count or not self.config_id.only_round_cash_method
                ),
                'name': init_data['payment_name'],
                'payment_method_id': init_data['payment_method_id'][0],
            })

        if order.state == 'draft' and order._is_pos_order_paid():
            order._process_saved_order(False)
            if order.state in {'paid', 'done'}:
                order._send_order()
                order.config_id.notify_synchronisation(order.config_id.current_session_id.id, 0)

            # Si es POS convencional, ejecutar automáticamente validar y facturar
            if is_conventional and order.state in {'paid', 'done'} and not order.account_move:
                _logger.info(
                    "POS Conventional: Ejecutando facturación automática para pedido %s",
                    order.name
                )
                try:
                    # Ejecutar la acción de validar y facturar
                    result = order.action_validate_and_invoice()
                    # Retornar la acción para que JS imprima el ticket
                    return result
                except Exception as e:
                    _logger.exception(
                        "Error al facturar automáticamente el pedido %s: %s",
                        order.name, str(e)
                    )
                    # Si falla la facturación, cerrar el wizard normalmente
                    return {'type': 'ir.actions.act_window_close'}

            return {'type': 'ir.actions.act_window_close'}

        return self.launch_payment()

