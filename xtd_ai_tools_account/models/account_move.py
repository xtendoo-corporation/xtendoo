from odoo import models

from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiDraftOnlyError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _xtd_ai_block(self, message):
        if self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(message)

    def action_post(self):
        self._xtd_ai_block(
            self.env._("El agente IA no puede contabilizar asientos ni facturas.")
        )
        return super().action_post()

    def _post(self, soft=True):
        self._xtd_ai_block(
            self.env._("El agente IA no puede contabilizar asientos ni facturas.")
        )
        return super()._post(soft=soft)

    def button_cancel(self):
        self._xtd_ai_block(
            self.env._("El agente IA no puede cancelar asientos ni facturas.")
        )
        return super().button_cancel()

    def action_register_payment(self):
        self._xtd_ai_block(self.env._("El agente IA no puede registrar pagos."))
        return super().action_register_payment()

    def unlink(self):
        self._xtd_ai_block(
            self.env._("El agente IA no puede borrar asientos ni facturas.")
        )
        return super().unlink()
