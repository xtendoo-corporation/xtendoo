from odoo import models

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

# Set ONLY by close_opportunity around the won/lost call of one confirmed card:
# it lifts the guard for that opportunity and nothing else (§6.5).
CLOSE_UNLOCK_KEY = "xtd_ai_unlock_crm_close"


class CrmLead(models.Model):
    """Guards (CONTRACT section 7): the AI agent never deletes opportunities and
    only wins or loses one through the confirmed ``close_opportunity`` card."""

    _inherit = "crm.lead"

    def _xtd_ai_close_unlocked(self):
        return len(self) == 1 and self.env.context.get(CLOSE_UNLOCK_KEY) == self.id

    def _xtd_ai_guard(self, what, unlockable=False):
        # Nothing to guard on an empty recordset (Odoo calls these internally)
        if not self or not self.env.context.get("xtd_ai_run"):
            return
        if unlockable and self._xtd_ai_close_unlocked():
            return
        raise XtdAiDraftOnlyError(
            self.env._("El agente IA no puede %s oportunidades.", what)
        )

    def action_set_won(self):
        self._xtd_ai_guard(self.env._("ganar"), unlockable=True)
        return super().action_set_won()

    def action_set_won_rainbowman(self):
        self._xtd_ai_guard(self.env._("ganar"))
        return super().action_set_won_rainbowman()

    def action_set_lost(self, **additional_values):
        self._xtd_ai_guard(self.env._("perder"), unlockable=True)
        return super().action_set_lost(**additional_values)

    def write(self, vals):
        if self.env.context.get("xtd_ai_run") and self:
            if vals.get("active") is False:
                self._xtd_ai_guard(self.env._("archivar o perder"), unlockable=True)
            stage_id = vals.get("stage_id")
            if stage_id and self.env["crm.stage"].browse(stage_id).is_won:
                self._xtd_ai_guard(
                    self.env._("mover a una etapa ganada"), unlockable=True
                )
        return super().write(vals)

    def unlink(self):
        self._xtd_ai_guard(self.env._("borrar"))
        return super().unlink()
