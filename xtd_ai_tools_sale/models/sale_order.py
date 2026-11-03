from odoo import models

from odoo.addons.xtd_ai.tools import is_unlocked
from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


class SaleOrder(models.Model):
    """Guards (CONTRACT section 7): inside an AI run nothing confirms, sends,
    locks, cancels or deletes sales orders, whatever triggers the call (a tool,
    an automated action, an override), except the one operation a confirmed
    card unlocked for that one order (``xtd_ai.tools.unlock``, §6.5):
    ``confirm_sale_order``, ``send_quotation_email``, ``cancel_sale_quotation``.
    Deleting is never unlocked."""

    _inherit = "sale.order"

    def _xtd_ai_guard(self, what, unlockable=()):
        # Nothing to guard on an empty recordset (Odoo calls these internally)
        if not self or not self.env.context.get("xtd_ai_run"):
            return
        if len(self) == 1 and any(is_unlocked(self, m) for m in unlockable):
            return
        raise XtdAiDraftOnlyError(
            self.env._(
                "El agente IA solo puede dejar presupuestos en borrador: no puede %s.",
                what,
            )
        )

    def action_confirm(self):
        self._xtd_ai_guard(self.env._("confirmar pedidos"), ("action_confirm",))
        return super().action_confirm()

    def _action_confirm(self):
        self._xtd_ai_guard(self.env._("confirmar pedidos"), ("action_confirm",))
        return super()._action_confirm()

    def action_quotation_send(self):
        self._xtd_ai_guard(self.env._("enviar presupuestos"), ("send_email",))
        return super().action_quotation_send()

    def action_lock(self):
        # the company may lock confirmed orders automatically
        self._xtd_ai_guard(self.env._("bloquear pedidos"), ("action_confirm",))
        return super().action_lock()

    def action_cancel(self):
        self._xtd_ai_guard(self.env._("cancelar pedidos"), ("action_cancel",))
        return super().action_cancel()

    def _action_cancel(self):
        self._xtd_ai_guard(self.env._("cancelar pedidos"), ("action_cancel",))
        return super()._action_cancel()

    def unlink(self):
        self._xtd_ai_guard(self.env._("borrar pedidos"))
        return super().unlink()
