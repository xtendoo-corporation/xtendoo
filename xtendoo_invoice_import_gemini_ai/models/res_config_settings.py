# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


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
        default="gemini-2.5-flash",
        help="Model to use for extraction. Available models:\n"
             "• gemini-2.5-flash (recommended, fast and efficient)\n"
             "• gemini-2.5-pro (high quality, more capable)\n"
             "• gemini-flash-latest (latest stable flash version)\n"
             "• gemini-pro-latest (latest stable pro version)\n"
             "• gemini-2.0-flash-exp (experimental)\n"
             "• gemini-2.5-flash-lite (lighter, faster)\n\n"
             "Note: Older models like gemini-pro, gemini-1.5-flash, gemini-1.5-pro are deprecated.\n"
             "Test your API key with 'Test Gemini Connection' to see all available models.",
    )
    gemini_auto_scan = fields.Selection(
        [
            ('disabled', 'Disabled'),
            ('full', 'Auto Scan (Full)'),
            ('summary', 'Auto Scan (Summary)'),
        ],
        string="Auto Scan on Upload",
        config_parameter="xtendoo_invoice_import_gemini_ai.gemini_auto_scan",
        default="disabled",
        help="Automatically scan vendor bills when a PDF/image is attached:\n"
             "• Disabled: Manual scan only (click buttons)\n"
             "• Auto Scan (Full): Extract all individual line items\n"
             "• Auto Scan (Summary): Group lines by VAT percentage",
    )

    def action_test_gemini_connection(self):
        """Test the Gemini API connection and list available models."""
        self.ensure_one()

        if not self.gemini_api_key:
            raise UserError(_("Please configure the Gemini API Key first."))

        if not genai:
            raise UserError(_("google-genai library is not installed. Please install it."))

        try:
            # Usar la nueva API con Client
            client = genai.Client(api_key=self.gemini_api_key)

            # Intentar listar modelos disponibles
            available_models = []
            try:
                models_response = client.models.list()
                for m in models_response:
                    # Los modelos tienen el nombre completo, extraemos solo el nombre
                    if hasattr(m, 'name'):
                        # Los nombres vienen como "models/gemini-xxx"
                        model_name = m.name
                        if model_name.startswith('models/'):
                            model_name = model_name.replace('models/', '')
                        available_models.append(model_name)
            except Exception as list_error:
                _logger.warning(f"Could not list models: {str(list_error)}")
                # Si no podemos listar, sugerimos los modelos comunes actuales
                available_models = [
                    "gemini-2.5-flash",
                    "gemini-2.5-pro",
                    "gemini-flash-latest",
                    "gemini-pro-latest",
                    "gemini-2.0-flash-exp",
                    "gemini-2.5-flash-lite",
                ]

            if available_models:
                models_list = "\n• ".join(available_models)
                message = _("✅ Connection successful!\n\nAvailable models:\n• %s\n\nUse one of these names in 'Gemini Model' field.") % models_list
            else:
                message = _("✅ Connection successful but no models found.")

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Gemini API Test"),
                    "message": message,
                    "type": "success",
                    "sticky": True,
                },
            }

        except Exception as e:
            _logger.error(f"Gemini API test failed: {str(e)}", exc_info=True)
            raise UserError(_("Connection failed: %s\n\nMake sure your API key is valid and you have internet access.") % str(e))
