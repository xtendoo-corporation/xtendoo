from odoo import api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


class AccountAnalyticLine(models.Model):
    """Guards (CONTRACT section 7): inside an AI run a timesheet is always the
    user's own, whatever rights the user has over other employees' hours."""

    _inherit = "account.analytic.line"

    def _xtd_ai_check_own_timesheets(self):
        if not self.env.context.get("xtd_ai_run"):
            return
        for line in self:
            if line.project_id and (
                line.user_id != self.env.user
                or line.employee_id.user_id != self.env.user
            ):
                raise XtdAiDraftOnlyError(
                    self.env._(
                        "El agente IA solo puede imputar horas del propio usuario."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._xtd_ai_check_own_timesheets()
        return lines

    def write(self, vals):
        self._xtd_ai_check_own_timesheets()
        result = super().write(vals)
        self._xtd_ai_check_own_timesheets()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_xtd_ai_run(self):
        if self and self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._("El agente IA no puede borrar partes de horas.")
            )
