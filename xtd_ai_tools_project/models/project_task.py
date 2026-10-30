from odoo import api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError


class ProjectTask(models.Model):
    """Guards (CONTRACT section 7): the AI agent never deletes tasks."""

    _inherit = "project.task"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_xtd_ai_run(self):
        if self and self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._("El agente IA no puede borrar tareas.")
            )
