# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _get_whatsapp_phone_preview_data(self):
        self.ensure_one()
        if self.gateway_id.gateway_type != "whatsapp" or not self.gateway_channel_token:
            return {}

        phone = self.gateway_channel_token
        sanitized_phone = phone if phone.startswith("+") else f"+{phone}"
        gateway_partners = self.env["res.partner.gateway.channel"].search(
            [
                ("gateway_id", "=", self.gateway_id.id),
                ("gateway_token", "=", str(phone).lstrip("+")),
            ],
            limit=5,
        ).partner_id
        partners = gateway_partners | self.env["res.partner"].search(
            [("phone_sanitized", "=", sanitized_phone)], limit=5
        )
        partners = partners[:5]
        partner_data = [
            {
                "id": partner.id,
                "name": partner.display_name,
                "phone": partner.phone or partner.phone_sanitized,
            }
            for partner in partners
        ]
        odoo_contact_label = ", ".join(partner["name"] for partner in partner_data)
        return {
            "whatsapp_phone": sanitized_phone,
            "whatsapp_partner_matches": partner_data,
            "whatsapp_odoo_contact_label": odoo_contact_label,
        }

    def _to_store_defaults(self, target: Store.Target):
        # En 19 no se puede llamar a store.add(channel, ...) dentro de _to_store (recursión infinita):
        # los campos extra se declaran aquí, como hace el core.
        res = super()._to_store_defaults(target)
        res += [
            Store.Attr(
                "whatsapp_phone",
                lambda channel: channel._get_whatsapp_phone_preview_data().get("whatsapp_phone") or False,
            ),
            Store.Attr(
                "whatsapp_odoo_contact_label",
                lambda channel: channel._get_whatsapp_phone_preview_data().get("whatsapp_odoo_contact_label") or False,
            ),
            Store.Attr(
                "whatsapp_partner_matches",
                lambda channel: channel._get_whatsapp_phone_preview_data().get("whatsapp_partner_matches") or [],
            ),
        ]
        return res
