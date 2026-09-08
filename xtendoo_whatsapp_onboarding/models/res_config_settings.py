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
