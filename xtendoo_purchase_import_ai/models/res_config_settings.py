# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    gemini_auto_scan_purchase = fields.Selection(
        [
            ("disabled", "Disabled"),
            ("full", "Full Scan (All Lines)"),
            ("summary", "Summarized Scan (By VAT Type)"),
        ],
        string="Auto-scan Purchase Orders",
        config_parameter="xtendoo_purchase_import_ai.gemini_auto_scan",
        default="disabled",
    )

