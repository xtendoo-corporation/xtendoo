# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    ai_enriched = fields.Boolean(
        string="Enriched by AI",
        default=False,
        copy=False,
        help="Indicates this lead has been enriched with AI-extracted data.",
    )
    ai_source_text = fields.Text(
        string="AI Source Text",
        copy=False,
        help="Original text used by AI to enrich this lead.",
    )

    def action_open_ai_enrichment_wizard(self):
        """Open the AI enrichment wizard for this lead."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Enrich Lead with AI"),
            "res_model": "crm.lead.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lead_id": self.id},
        }
