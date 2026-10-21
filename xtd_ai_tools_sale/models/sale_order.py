from odoo import models

from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiDraftOnlyError


class SaleOrder(models.Model):
    """Draft-only guards (CONTRACT section 7): the AI agent never confirms, sends,
    locks, cancels or deletes sales orders, whatever triggers the call (a tool,
    an automated action, an override)."""

    _inherit = "sale.order"

    def _xtd_ai_guard(self, what):
        if self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA solo puede dejar presupuestos en borrador: no "
                    "puede %s.",
                    what,
                )
            )

    def action_confirm(self):
        self._xtd_ai_guard(self.env._("confirmar pedidos"))
        return super().action_confirm()

    def _action_confirm(self):
        self._xtd_ai_guard(self.env._("confirmar pedidos"))
        return super()._action_confirm()

    def action_quotation_send(self):
        self._xtd_ai_guard(self.env._("enviar presupuestos"))
        return super().action_quotation_send()

    def action_lock(self):
        self._xtd_ai_guard(self.env._("bloquear pedidos"))
        return super().action_lock()

    def action_cancel(self):
        self._xtd_ai_guard(self.env._("cancelar pedidos"))
        return super().action_cancel()

    def _action_cancel(self):
        self._xtd_ai_guard(self.env._("cancelar pedidos"))
        return super()._action_cancel()

    def unlink(self):
        self._xtd_ai_guard(self.env._("borrar pedidos"))
        return super().unlink()
