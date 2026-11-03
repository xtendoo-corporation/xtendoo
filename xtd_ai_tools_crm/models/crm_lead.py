from odoo import models

from odoo.addons.xtd_ai.tools import is_unlocked
from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


class CrmLead(models.Model):
    """Guards (CONTRACT section 7): the AI agent never deletes opportunities and
    only wins or loses one through the confirmed ``close_opportunity`` card."""

    _inherit = "crm.lead"

    def _xtd_ai_close_unlocked(self, method):
        """``close_opportunity`` lifted this guard for this one opportunity
        (``xtd_ai.tools.unlock``, §6.5)."""
        return is_unlocked(self, method)

    def _xtd_ai_guard(self, what, unlockable=()):
        # Nothing to guard on an empty recordset (Odoo calls these internally)
        if not self or not self.env.context.get("xtd_ai_run"):
            return
        if any(self._xtd_ai_close_unlocked(m) for m in unlockable):
            return
        raise XtdAiDraftOnlyError(
            self.env._("El agente IA no puede %s oportunidades.", what)
        )

    def action_set_won(self):
        self._xtd_ai_guard(self.env._("ganar"), unlockable=("action_set_won",))
        return super().action_set_won()

    def action_set_won_rainbowman(self):
        self._xtd_ai_guard(self.env._("ganar"))
        return super().action_set_won_rainbowman()

    def action_set_lost(self, **additional_values):
        self._xtd_ai_guard(self.env._("perder"), unlockable=("action_set_lost",))
        return super().action_set_lost(**additional_values)

    def write(self, vals):
        if self.env.context.get("xtd_ai_run") and self:
            if vals.get("active") is False:
                self._xtd_ai_guard(
                    self.env._("archivar o perder"), unlockable=("action_set_lost",)
                )
            stage_id = vals.get("stage_id")
            if stage_id and self.env["crm.stage"].browse(stage_id).is_won:
                self._xtd_ai_guard(
                    self.env._("mover a una etapa ganada"),
                    unlockable=("action_set_won",),
                )
        return super().write(vals)

    def unlink(self):
        self._xtd_ai_guard(self.env._("borrar"))
        return super().unlink()
