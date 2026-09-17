# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xtendoo_whatsapp_relay_api_key = fields.Char(
        string="WhatsApp Relay API Key",
        help=(
            "Shared secret clients must send (header X-Xtendoo-Relay-Key) "
            "to register/unregister at /xtendoo_whatsapp_relay/register and "
            "/unregister. Must match the value configured on each client's "
            "xtendoo_whatsapp_onboarding settings."
        ),
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            xtendoo_whatsapp_relay_api_key=icp.get_param(
                "xtendoo_whatsapp_webhook_relay.api_key", default=""
            ),
        )
        return res

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "xtendoo_whatsapp_webhook_relay.api_key",
            self.xtendoo_whatsapp_relay_api_key or "",
        )
