# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    whatsapp_channel_count = fields.Integer(
        string="WhatsApp Conversations", compute="_compute_whatsapp_channel_count"
    )

    def _compute_whatsapp_channel_count(self):
        """Count WhatsApp channels for this partner."""
        for partner in self:
            channels = self.env["discuss.channel"].search(
                [
                    ("gateway_id.gateway_type", "=", "whatsapp"),
                    ("partner_id", "=", partner.id),
                ]
            )
            partner.whatsapp_channel_count = len(channels)

    def action_open_whatsapp_channels(self):
        """Open all WhatsApp conversations for this partner."""
        self.ensure_one()
        return {
            "name": "WhatsApp Conversations",
            "type": "ir.actions.act_window",
            "res_model": "discuss.channel",
            "view_mode": "list,form",
            "domain": [
                ("gateway_id.gateway_type", "=", "whatsapp"),
                ("partner_id", "=", self.id),
            ],
        }

