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


class XtdAiUndo(models.AbstractModel):
    """Undo of «move to another stage»: back to the stage before, from the
    user's session, if nobody moved it since."""

    _inherit = "xtd.ai.undo"

    def _xtd_ai_transition_crm_stage_reason(self, lead, edit):
        after = (edit.get("after") or {}).get("stage_id")
        before = self.env["crm.stage"].browse(
            (edit.get("before") or {}).get("stage_id")
        )
        if not lead.active or lead.stage_id.is_won:
            return self.env._("La oportunidad ya está cerrada.")
        if lead.stage_id.id != after:
            return self.env._("Alguien la ha movido de etapa después.")
        if not before.exists():
            return self.env._("La etapa anterior ya no existe.")
        return None

    def _xtd_ai_transition_crm_stage_done(self, lead, edit):
        before = (edit.get("before") or {}).get("stage_id")
        after = (edit.get("after") or {}).get("stage_id")
        return bool(before) and before != after and lead.stage_id.id == before

    def _xtd_ai_transition_crm_stage_apply(self, lead, edit):
        lead.write({"stage_id": edit["before"]["stage_id"]})
