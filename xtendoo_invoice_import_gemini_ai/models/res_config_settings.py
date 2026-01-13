# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    gemini_api_key = fields.Char(
        string="Gemini API Key",
        config_parameter="xtendoo_invoice_import_gemini_ai.gemini_api_key",
        help="API key for Google Gemini AI. Get it from https://aistudio.google.com/",
    )
    gemini_model = fields.Char(
        string="Gemini Model",
        config_parameter="xtendoo_invoice_import_gemini_ai.gemini_model",
        default="gemini-1.5-flash",
        help="Model to use for extraction (e.g., gemini-1.5-flash or gemini-1.5-pro)",
    )
