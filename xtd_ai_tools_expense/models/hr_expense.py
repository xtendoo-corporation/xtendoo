from odoo import api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

# Workflow steps the agent never runs: they notify a manager, decide on
# someone else's expense, post accounting or pay (§4 RRHH, §5).
BLOCKED_ACTIONS = (
    "action_submit",
    "action_approve",
    "_do_approve",
    "action_refuse",
    "_do_refuse",
    "action_post",
    "action_pay",
    "action_reset",
    "action_split_wizard",
    "action_approve_duplicates",
)


class HrExpense(models.Model):
    """Guards (CONTRACT section 7): inside an AI run an expense is always a
    draft of the user's own employee."""

    _inherit = "hr.expense"

    def _xtd_ai_check_own_draft(self):
        if not self.env.context.get("xtd_ai_run"):
            return
        for expense in self:
            if expense.employee_id.user_id != self.env.user:
                raise XtdAiDraftOnlyError(
                    self.env._("El agente IA solo puede preparar gastos propios.")
                )
            if expense.state != "draft":
                raise XtdAiDraftOnlyError(
                    self.env._("El agente IA solo puede tocar gastos en borrador.")
                )

    def _xtd_ai_guard(self):
        if self and self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA no puede enviar, aprobar, rechazar, contabilizar "
                    "ni pagar gastos."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        expenses = super().create(vals_list)
        expenses._xtd_ai_check_own_draft()
        return expenses

    def write(self, vals):
        self._xtd_ai_check_own_draft()
        if self and self.env.context.get("xtd_ai_run") and "approval_state" in vals:
            self._xtd_ai_guard()
        result = super().write(vals)
        self._xtd_ai_check_own_draft()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_xtd_ai_run(self):
        if self and self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._("El agente IA no puede borrar gastos.")
            )

    def action_submit(self):
        self._xtd_ai_guard()
        return super().action_submit()

    def action_approve(self):
        self._xtd_ai_guard()
        return super().action_approve()

    def _do_approve(self, *args, **kwargs):
        self._xtd_ai_guard()
        return super()._do_approve(*args, **kwargs)

    def action_refuse(self):
        self._xtd_ai_guard()
        return super().action_refuse()

    def _do_refuse(self, *args, **kwargs):
        self._xtd_ai_guard()
        return super()._do_refuse(*args, **kwargs)

    def action_post(self):
        self._xtd_ai_guard()
        return super().action_post()

    def action_pay(self):
        self._xtd_ai_guard()
        return super().action_pay()

    def action_reset(self):
        self._xtd_ai_guard()
        return super().action_reset()

    def action_split_wizard(self):
        self._xtd_ai_guard()
        return super().action_split_wizard()

    def action_approve_duplicates(self):
        self._xtd_ai_guard()
        return super().action_approve_duplicates()
