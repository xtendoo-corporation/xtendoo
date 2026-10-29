from odoo import models

from odoo.addons.xtd_ai.tools import check_draft_only


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _xtd_ai_guard(self):
        if not self:
            return  # nothing to guard on an empty recordset (Odoo calls it internally)
        check_draft_only(
            self.env,
            self.env._(
                "El agente IA no puede confirmar, reservar, validar ni borrar "
                "albaranes: "
                "lo hace una persona."
            ),
        )

    def button_validate(self):
        self._xtd_ai_guard()
        return super().button_validate()

    def action_confirm(self):
        self._xtd_ai_guard()
        return super().action_confirm()

    def action_assign(self):
        self._xtd_ai_guard()
        return super().action_assign()

    def _action_done(self):
        self._xtd_ai_guard()
        return super()._action_done()

    def unlink(self):
        self._xtd_ai_guard()
        return super().unlink()
