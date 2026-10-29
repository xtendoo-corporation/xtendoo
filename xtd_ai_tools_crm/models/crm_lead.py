from odoo import models

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


class CrmLead(models.Model):
    """Draft-only guards (CONTRACT section 7): the AI agent never wins, loses or
    deletes opportunities."""

    _inherit = "crm.lead"

    def _xtd_ai_guard(self, what):
        # Nothing to guard on an empty recordset (Odoo calls these internally)
        if self and self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._("El agente IA no puede %s oportunidades.", what)
            )

    def action_set_won(self):
        self._xtd_ai_guard(self.env._("ganar"))
        return super().action_set_won()

    def action_set_won_rainbowman(self):
        self._xtd_ai_guard(self.env._("ganar"))
        return super().action_set_won_rainbowman()

    def action_set_lost(self, **additional_values):
        self._xtd_ai_guard(self.env._("perder"))
        return super().action_set_lost(**additional_values)

    def write(self, vals):
        if self.env.context.get("xtd_ai_run") and self:
            if vals.get("active") is False:
                self._xtd_ai_guard(self.env._("archivar o perder"))
            stage_id = vals.get("stage_id")
            if stage_id and self.env["crm.stage"].browse(stage_id).is_won:
                self._xtd_ai_guard(self.env._("mover a una etapa ganada"))
        return super().write(vals)

    def unlink(self):
        self._xtd_ai_guard(self.env._("borrar"))
        return super().unlink()
