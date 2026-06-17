# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from odoo import models, fields, _
_logger = logging.getLogger(__name__)
class HrExpense(models.Model):
    _inherit = "hr.expense"
    ai_document_type = fields.Selection(
        selection=[
            ("expense", "Gasto"),
            ("other", "Otro"),
        ],
        string="Tipo de Documento Detectado",
        copy=False,
        readonly=True,
        help="Tipo de documento detectado automáticamente por la IA.",
    )
    ai_processed = fields.Boolean(
        string="Procesado por IA",
        default=False,
        copy=False,
    )
    ai_has_corrections = fields.Boolean(
        string="Correcciones de IA Pendientes",
        default=False,
        copy=False,
        help="Indica si se han realizado correcciones manuales tras el procesamiento por IA.",
    )
    def action_open_ai_document_wizard(self):
        """Open the AI document import wizard for this expense."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Importar Documento con IA"),
            "res_model": "hr.expense.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_expense_id": self.id},
        }
    def write(self, vals):
        """Re-activate ai_has_corrections when user edits after AI processing."""
        ai_internal_fields = {
            "ai_document_type",
            "ai_processed",
            "ai_has_corrections",
        }
        user_changed = set(vals.keys()) - ai_internal_fields
        if user_changed and "ai_has_corrections" not in vals:
            for rec in self:
                if rec.ai_processed:
                    vals["ai_has_corrections"] = True
                    break
        return super().write(vals)
