# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xtendoo_whatsapp_meta_app_id = fields.Char(
        string="Meta App ID",
        help="Xtendoo's Meta App ID used for WhatsApp Embedded Signup.",
    )
    xtendoo_whatsapp_meta_app_secret = fields.Char(
        string="Meta App Secret",
        help=(
            "Xtendoo's Meta App Secret. Used server-side only to exchange "
            "the Embedded Signup authorization code for an access token. "
            "Never sent to the browser."
        ),
    )
    xtendoo_whatsapp_meta_config_id = fields.Char(
        string="Embedded Signup Configuration ID",
        help=(
            "Configuration ID of the Facebook Login for Business "
            "configuration used for WhatsApp Embedded Signup."
        ),
    )
    xtendoo_whatsapp_meta_graph_version = fields.Char(
        string="Graph API Version",
        default="21.0",
        help="Meta Graph API version used for all onboarding requests.",
    )
    xtendoo_whatsapp_meta_system_user_token = fields.Char(
        string="Xtendoo System User Token (no expiry)",
        help=(
            "Optional. A long-lived System User access token from Xtendoo's "
            "own Meta Business Manager (Business Settings > Users > System "
            "Users), generated WITHOUT the '60 days' expiry option. When "
            "set, it is used instead of each client's own Embedded Signup "
            "token for sending messages and importing templates, so clients "
            "never need to reconnect when their per-signup token expires. "
            "Leave empty to keep using each client's own token as-is."
        ),
    )
    xtendoo_whatsapp_relay_register_url = fields.Char(
        string="Relay Register URL",
        help=(
            "Full URL of Xtendoo's own production Odoo relay endpoint, e.g. "
            "https://xtdeoo.es/xtendoo_whatsapp_relay/register. Meta only "
            "allows a single Callback URL for the whole app, so every "
            "client's incoming messages arrive there first and get "
            "forwarded here. Required to actually receive messages; leave "
            "empty to only be able to send."
        ),
    )
    xtendoo_whatsapp_relay_unregister_url = fields.Char(
        string="Relay Unregister URL",
        help="Same host as the register URL, e.g. .../xtendoo_whatsapp_relay/unregister.",
    )
    xtendoo_whatsapp_relay_api_key = fields.Char(
        string="Relay API Key",
        help=(
            "Shared secret sent as the X-Xtendoo-Relay-Key header when "
            "registering/unregistering with the relay. Must match the key "
            "configured on Xtendoo's relay (xtendoo_whatsapp_webhook_relay)."
        ),
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            xtendoo_whatsapp_meta_app_id=icp.get_param(
                "xtendoo_whatsapp_onboarding.meta_app_id", default=""
            ),
            xtendoo_whatsapp_meta_app_secret=icp.get_param(
                "xtendoo_whatsapp_onboarding.meta_app_secret", default=""
            ),
            xtendoo_whatsapp_meta_config_id=icp.get_param(
                "xtendoo_whatsapp_onboarding.meta_config_id", default=""
            ),
            xtendoo_whatsapp_meta_graph_version=icp.get_param(
                "xtendoo_whatsapp_onboarding.meta_graph_version", default="21.0"
            ),
            xtendoo_whatsapp_meta_system_user_token=icp.get_param(
                "xtendoo_whatsapp_onboarding.meta_system_user_token", default=""
            ),
            xtendoo_whatsapp_relay_register_url=icp.get_param(
                "xtendoo_whatsapp_onboarding.relay_register_url", default=""
            ),
            xtendoo_whatsapp_relay_unregister_url=icp.get_param(
                "xtendoo_whatsapp_onboarding.relay_unregister_url", default=""
            ),
            xtendoo_whatsapp_relay_api_key=icp.get_param(
                "xtendoo_whatsapp_onboarding.relay_api_key", default=""
            ),
        )
        return res

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "xtendoo_whatsapp_onboarding.meta_app_id",
            self.xtendoo_whatsapp_meta_app_id or "",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.meta_app_secret",
            self.xtendoo_whatsapp_meta_app_secret or "",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.meta_config_id",
            self.xtendoo_whatsapp_meta_config_id or "",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.meta_graph_version",
            self.xtendoo_whatsapp_meta_graph_version or "21.0",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.meta_system_user_token",
            self.xtendoo_whatsapp_meta_system_user_token or "",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.relay_register_url",
            self.xtendoo_whatsapp_relay_register_url or "",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.relay_unregister_url",
            self.xtendoo_whatsapp_relay_unregister_url or "",
        )
        icp.set_param(
            "xtendoo_whatsapp_onboarding.relay_api_key",
            self.xtendoo_whatsapp_relay_api_key or "",
        )
