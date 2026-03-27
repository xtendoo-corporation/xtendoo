import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosMakePaymentWizard(models.TransientModel):
    _name = "pos.make.payment.wizard"
    _description = "Asistente de Pago POS"

    order_id = fields.Many2one("pos.order", string="Pedido", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="order_id.currency_id", depends=["order_id"])
    amount_total = fields.Monetary(related="order_id.amount_total", string="Total Pedido", readonly=True)
    amount_paid = fields.Monetary(string="Pagado", compute="_compute_totals")
    amount_due = fields.Monetary(string="Total a Pagar", compute="_compute_totals")
    
    # Este importe representa cuánto va a entregar el cliente
    amount_tendered = fields.Monetary(string="Importe Entregado", default=0.0)
    
    amount_change = fields.Monetary(string="Cambio a Devolver", compute="_compute_amount_change")
    is_cash_payment = fields.Boolean(compute="_compute_is_cash_payment")
    
    # Campo para ver todos los pagos en esta sesión
    payment_ids = fields.Many2many(comodel_name="pos.payment", compute="_compute_payment_ids", string="Pagos Registrados")
    
    # Campo para el nuevo pago a añadir
    payment_method_id = fields.Many2one("pos.payment.method", string="Diario", domain="[('id', 'in', available_payment_method_ids)]")

    @api.depends("order_id.payment_ids")
    def _compute_payment_ids(self):
        for wiz in self:
            wiz.payment_ids = wiz.order_id.payment_ids

    @api.depends("payment_method_id")
    def _compute_is_cash_payment(self):
        for wiz in self:
            wiz.is_cash_payment = wiz.payment_method_id.is_cash_count or wiz.payment_method_id.journal_id.type == 'cash'

    @api.depends("amount_tendered", "amount_due", "amount_paid", "amount_total", "is_cash_payment")
    def _compute_amount_change(self):
        for wiz in self:
            # El cambio es lo que sobra del (Pagado + Entregado actualmente) respecto al Total
            total_with_tendered = wiz.amount_paid + wiz.amount_tendered
            if wiz.is_cash_payment and total_with_tendered > wiz.amount_total:
                wiz.amount_change = total_with_tendered - wiz.amount_total
            else:
                wiz.amount_change = 0.0
    
    # Seleccionables
    config_id = fields.Many2one(related="order_id.config_id")
    available_payment_method_ids = fields.Many2many(
        "pos.payment.method", 
        compute="_compute_available_payment_methods"
    )

    @api.depends("order_id.amount_total", "order_id.payment_ids", "order_id.payment_ids.amount")
    def _compute_totals(self):
        for wiz in self:
            paid = sum(wiz.order_id.payment_ids.mapped('amount'))
            wiz.amount_paid = paid
            due = wiz.order_id.amount_total - paid
            wiz.amount_due = due if due > 0 else 0.0

    @api.depends("config_id")
    def _compute_available_payment_methods(self):
        for wiz in self:
            if self._context.get('cash_only'):
                wiz.available_payment_method_ids = wiz.config_id.payment_method_ids.filtered(
                    lambda p: p.is_cash_count or p.journal_id.type == 'cash'
                )
            else:
                wiz.available_payment_method_ids = wiz.config_id.payment_method_ids

    @api.model
    def default_get(self, fields_list):
        res = super(PosMakePaymentWizard, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            if order.exists():
                res['order_id'] = order.id
                
                # Forzar recálculo para evitar que el Total a Pagar salga a cero
                try:
                    order._compute_prices()
                except Exception:
                    order.amount_total = sum(order.lines.mapped('price_subtotal_incl'))
                    
                # Pre-cargar el importe pendiente a entregar
                due = order.amount_total - order.amount_paid
                res['amount_tendered'] = due if due > 0 else 0.0
                
                # Pre-cargar el método de pago
                payment_methods = order.config_id.payment_method_ids
                if self._context.get('cash_only'):
                    payment_methods = payment_methods.filtered(lambda p: p.is_cash_count or p.journal_id.type == 'cash')
                
                # Intentar usar el valor pasado por contexto o el primer cash_method
                default_pm = self._context.get('default_payment_method_id')
                if default_pm:
                    res['payment_method_id'] = default_pm
                elif payment_methods:
                    # Buscar el primer cash method si no hay uno por defecto
                    cash_pm = payment_methods.filtered(lambda p: p.is_cash_count or p.journal_id.type == 'cash')[:1]
                    res['payment_method_id'] = cash_pm.id if cash_pm else payment_methods[0].id
        return res

    def _add_payment(self, payment_method_id):
        """Función auxiliar para añadir un pago al pedido subyacente"""
        self.ensure_one()
        if self.amount_tendered <= 0.0:
            raise UserError(_("Debe ingresar un importe mayor a cero o el pedido ya está pagado."))
            
        payment_method = self.env['pos.payment.method'].browse(payment_method_id)
        if not payment_method.exists():
            raise UserError(_("Método de pago no válido."))

        self.order_id.add_payment({
            'pos_order_id': self.order_id.id,
            'amount': self.amount_tendered,
            'payment_method_id': payment_method.id,
        })
        
        # Ajustar importe_entregado si aún falta
        due = self.order_id.amount_total - self.order_id.amount_paid
        self.amount_tendered = due if due > 0 else 0.0

        # Refrescar vista
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.make.payment.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_pay_cash(self):
        """Se presiona el botón Efectivo"""
        cash_method = self.env["pos.payment.method"].search(
            [("is_cash_count", "=", True)], limit=1
        )
        if not cash_method:
            cash_method = self.env["pos.payment.method"].search(
                [("journal_id.type", "=", "cash")], limit=1
            )
        if not cash_method:
            raise UserError(_("No se encontró método de pago en efectivo."))
            
        return self._add_payment(cash_method.id)

    def action_pay_card(self):
        """Añade un pago por tarjeta usando el importe entregado o el pendiente."""
        self.ensure_one()
        card_method = self.env["pos.payment.method"].search(
            [("name", "ilike", "tarjeta")], limit=1
        )
        if not card_method:
            raise UserError(_("No se encontró método de pago con tarjeta."))
            
        return self._add_payment(card_method.id)
        
    def action_add_payment(self):
        """Añade el pago seleccionado al pedido"""
        self.ensure_one()
        if not self.payment_method_id:
            raise UserError(_("Debe seleccionar un método de pago."))
        return self._add_payment(self.payment_method_id.id)
        
    def action_delete_payment(self):
        """Elimina el pago seleccionado (el que lanzó la acción desde la línea)"""
        # Esta acción se llamará con el ID del pago en el contexto si usamos un botón en el tree
        # Pero podemos usar el borrado estándar del many2many si lo permitimos.
        # Por ahora, implementamos action_clear_payments para borrar TODOS.
        pass

    def action_clear_payments(self):
        """Elimina todos los pagos para poder corregir si el cajero se equivoca."""
        self.ensure_one()
        # Borrar los pagos asociados al pedido
        if self.order_id.payment_ids:
            self.order_id.payment_ids.unlink()
        
        # Refrescar la vista actualizando el importe entregado al total del pedido
        self.amount_tendered = self.amount_total
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.make.payment.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
        
    def _execute_validation(self, print_invoice=False):
        """Valida exactamente igual que las acciones de los botones nativos de pago"""
        self.ensure_one()
        if self.amount_due > 0.01:
            raise UserError(_("Falta importe por pagar."))
            
        order = self.order_id
        is_conventional = order.config_id and order.config_id.pos_non_touch
        
        if order.state == "draft" and order.amount_paid >= order.amount_total - 0.01:
            # Si hay sobrepago (cambio), registrarlo como un pago negativo para cuadrar el pedido
            change = order.amount_paid - order.amount_total
            if change > 0.01:
                cash_method = order.config_id.payment_method_ids.filtered('is_cash_count')[:1]
                if not cash_method:
                    cash_method = order.config_id.payment_method_ids.filtered(lambda p: p.journal_id.type == 'cash')[:1]
                
                if cash_method:
                    order.add_payment({
                        'pos_order_id': order.id,
                        'amount': -change,
                        'payment_method_id': cash_method.id,
                    })

            order._process_saved_order(False)
            if order.state in {"paid", "done"}:
                order._send_order()
                order.config_id.notify_synchronisation(order.config_id.current_session_id.id, 0)
                
            should_print = print_invoice or order.config_id.iface_print_auto
            if should_print and is_conventional and order.state in {"paid", "done"} and not order.account_move:
                try:
                    result = order.action_validate_and_invoice()
                    if result and isinstance(result, dict) and result.get("type") == "ir.actions.client":
                        params = result.get("params", {})
                        if not params.get("next_action"):
                            result.setdefault("params", {})["next_action"] = {
                                "type": "ir.actions.client",
                                "tag": "pos_conventional_new_order",
                                "params": {
                                    "config_id": order.config_id.id,
                                    "session_id": order.config_id.current_session_id.id,
                                },
                            }
                        return result
                except Exception as e:
                    _logger.exception("Error en factura automática: %s", str(e))
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
            
        return {"type": "ir.actions.act_window_close"}

    def action_validate(self):
        """Validar sin imprimir (botón VALIDAR >)"""
        return self._execute_validation(print_invoice=False)

    def action_validate_print(self):
        """Validar e imprimir (botón VALIDAR E IMPRIMIR)"""
        return self._execute_validation(print_invoice=True)
