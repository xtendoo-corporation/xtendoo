# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import models
from odoo.exceptions import UserError
from odoo import _
from .ai_provider import build_provider, AIProvider

_logger = logging.getLogger(__name__)


class AIConnectorMixin(models.AbstractModel):
    """
    Mixin that provides a helper to get a ready-to-use AIProvider instance
    based on the global configuration stored in ir.config_parameter.

    Inherit from this mixin in any model that needs to call an AI provider:

        class MyModel(models.Model):
            _name = "my.model"
            _inherit = ["my.model", "xtendoo.ai.connector.mixin"]

        def my_method(self):
            provider = self._get_ai_provider()
            result = provider.send_prompt("Hello AI", files=[...])
    """

    _name = "xtendoo.ai.connector.mixin"
    _description = "AI Connector Mixin"

    def _get_ai_provider(self) -> AIProvider:
        """
        Build and return an AIProvider instance using the global configuration.

        :raises UserError: If the API key is not configured.
        :raises ValueError: If the provider name is unknown.
        """
        get_param = self.env["ir.config_parameter"].sudo().get_param
        provider_name = get_param("xtendoo_ai_connector.ai_provider", "gemini")
        api_key = get_param("xtendoo_ai_connector.ai_api_key", "")
        model = get_param("xtendoo_ai_connector.ai_model", "")

        if not api_key:
            raise UserError(
                _(
                    "AI API Key is not configured. "
                    "Please go to Settings → AI Connector and set your API key."
                )
            )

        try:
            return build_provider(provider_name, api_key, model)
        except (ValueError, ImportError) as exc:
            raise UserError(str(exc)) from exc
