# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def action_open_ai_import_wizard(self):
        """Abrir wizard de importación de facturas con IA desde el dashboard del diario"""
        self.ensure_one()

        return {
            "name": "Importar Factura con IA (OCR)",
            "type": "ir.actions.act_window",
            "res_model": "xtendoo.invoice.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_company_id": self.company_id.id,
                "default_journal_id": self.id,
                "default_create_partner_if_missing": True,
                "default_attach_original": True,
            },
        }

