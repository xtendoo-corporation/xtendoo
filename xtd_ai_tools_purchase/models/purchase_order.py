from odoo import models

from odoo.addons.xtd_ai.tools import check_draft_only


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _xtd_ai_guard(self):
        if not self:
            return  # nothing to guard on an empty recordset (Odoo calls it internally)
        check_draft_only(
            self.env,
            self.env._(
                "El agente IA solo puede crear solicitudes de presupuesto en borrador: "
                "confirmar, aprobar, enviar, cancelar o borrar pedidos de compra lo "
                "hace una persona."
            ),
        )

    def button_confirm(self):
        self._xtd_ai_guard()
        return super().button_confirm()

    def button_approve(self, force=False):
        self._xtd_ai_guard()
        return super().button_approve(force=force)

    def action_rfq_send(self):
        self._xtd_ai_guard()
        return super().action_rfq_send()

    def button_cancel(self):
        self._xtd_ai_guard()
        return super().button_cancel()

    def unlink(self):
        self._xtd_ai_guard()
        return super().unlink()
