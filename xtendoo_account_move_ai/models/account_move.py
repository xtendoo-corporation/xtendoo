# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_document_type = fields.Selection(
        selection=[
            ("salary", "Payslip / Salary"),
            ("expense", "Expense"),
            ("income", "Income"),
            ("other", "Other"),
        ],
        string="Detected Document Type",
        copy=False,
        readonly=True,
        help=(
            "Document type auto-detected by AI. "
            "You can correct it manually if the detection is wrong."
        ),
    )
    ai_document_type_editable = fields.Boolean(
        string="Allow Document Type Override",
        default=False,
        copy=False,
        help="Enable to override the AI-detected document type manually.",
    )
    ai_processed = fields.Boolean(
        string="Processed by AI",
        default=False,
        copy=False,
    )
    ai_has_corrections = fields.Boolean(
        string="Pending AI Feedback",
        default=False,
        copy=False,
        help="Indicates manual corrections have been made after AI processing.",
    )

    def action_open_ai_document_wizard(self):
        """Open the AI document import wizard for this journal entry."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Document with AI"),
            "res_model": "account.move.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def write(self, vals):
        """Re-activate ai_has_corrections when user edits after AI processing."""
        ai_internal_fields = {
            "ai_document_type",
            "ai_processed",
            "ai_has_corrections",
            "ai_document_type_editable",
        }
        user_changed = set(vals.keys()) - ai_internal_fields
        if user_changed and "ai_has_corrections" not in vals:
            for rec in self:
                if rec.ai_processed:
                    vals["ai_has_corrections"] = True
                    break
        return super().write(vals)
