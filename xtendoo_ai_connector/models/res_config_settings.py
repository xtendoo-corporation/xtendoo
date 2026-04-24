# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import _, fields, models
from odoo.exceptions import UserError
from .ai_provider import build_provider

_logger = logging.getLogger(__name__)

PROVIDER_DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "claude": "claude-opus-4-5",
}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_provider = fields.Selection(
        selection=[
            ("gemini", "Google Gemini"),
            ("openai", "OpenAI (ChatGPT)"),
            ("claude", "Anthropic Claude"),
        ],
        string="AI Provider",
        config_parameter="xtendoo_ai_connector.ai_provider",
        default="gemini",
        required=True,
        help="AI provider to use for all AI-powered modules.",
    )
    ai_model = fields.Char(
        string="AI Model",
        config_parameter="xtendoo_ai_connector.ai_model",
        default="gemini-2.5-flash",
        help=(
            "Model identifier for the selected provider.\n"
            "• Gemini: gemini-2.5-flash, gemini-2.5-pro, gemini-flash-latest\n"
            "• OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo\n"
            "• Claude: claude-opus-4-5, claude-sonnet-4-5, claude-haiku-3-5"
        ),
    )
    ai_api_key = fields.Char(
        string="AI API Key",
        config_parameter="xtendoo_ai_connector.ai_api_key",
        help="API key for the selected AI provider.",
    )

    def action_test_ai_connection(self):
        """Test the AI connection and list available models."""
        self.ensure_one()

        provider_name = self.ai_provider
        api_key = self.ai_api_key
        model = self.ai_model

        if not api_key:
            raise UserError(_("Please configure the AI API Key first."))

        try:
            provider = build_provider(provider_name, api_key, model)
            available_models = provider.list_models()
        except ImportError as exc:
            raise UserError(
                _("Required library not installed: %s") % str(exc)
            ) from exc
        except Exception as exc:
            _logger.error("AI connection test failed: %s", exc, exc_info=True)
            raise UserError(
                _(
                    "Connection failed: %s\n\n"
                    "Make sure your API key is valid and you have internet access."
                ) % str(exc)
            ) from exc

        if available_models:
            models_list = "\n• ".join(available_models[:30])
            message = _(
                "✅ Connection successful!\n\nAvailable models (first 30):\n• %s\n\n"
                "Use one of these names in the 'AI Model' field."
            ) % models_list
        else:
            message = _("✅ Connection successful.")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("AI Connection Test"),
                "message": message,
                "type": "success",
                "sticky": True,
            },
        }
