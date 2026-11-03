from odoo import models

from odoo.addons.xtd_ai.tools import check_draft_only, is_unlocked


class PurchaseOrder(models.Model):
    """Guards (CONTRACT section 7): inside an AI run nothing confirms, approves,
    sends, cancels or deletes purchase orders, except the one operation a
    confirmed card unlocked for that one order (``confirm_purchase_order``,
    ``cancel_purchase_rfq``, §6.5). Approving above the double validation
    amount keeps the user's own rights: Odoo leaves it «to approve»."""

    _inherit = "purchase.order"

    def _xtd_ai_guard(self, unlockable=()):
        if not self:
            return  # nothing to guard on an empty recordset (Odoo calls it internally)
        if len(self) == 1 and any(is_unlocked(self, m) for m in unlockable):
            return
        check_draft_only(
            self.env,
            self.env._(
                "El agente IA solo puede crear solicitudes de presupuesto en borrador: "
                "confirmar, aprobar, enviar, cancelar o borrar pedidos de compra lo "
                "hace una persona."
            ),
        )

    def button_confirm(self):
        self._xtd_ai_guard(("button_confirm",))
        return super().button_confirm()

    def button_approve(self, force=False):
        # button_confirm approves by itself when no double validation applies
        self._xtd_ai_guard(("button_confirm",))
        return super().button_approve(force=force)

    def action_rfq_send(self):
        self._xtd_ai_guard()
        return super().action_rfq_send()

    def button_cancel(self):
        self._xtd_ai_guard(("button_cancel",))
        return super().button_cancel()

    def unlink(self):
        self._xtd_ai_guard()
        return super().unlink()
