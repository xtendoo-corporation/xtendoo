# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import UserError


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _thread_to_store(self, store: Store, /, *, request_list=None, **kwargs):
        """Add canSendWhatsapp to thread data for chatter button."""
        super()._thread_to_store(store, request_list=request_list, **kwargs)

        if request_list:
            # Check if there's at least one WhatsApp gateway available
            has_whatsapp_gateway = bool(
                self.env["mail.gateway"].search(
                    [("gateway_type", "=", "whatsapp")], limit=1
                )
            )

            # Check if the model has phone fields (partner, mobile, etc)
            can_send = False
            if has_whatsapp_gateway:
                # Check if record has valid phone field method
                if hasattr(self, "_phone_get_number_fields"):
                    phone_fields = self._phone_get_number_fields()
                    can_send = bool(phone_fields)
                # Fallback: check common fields
                elif any(f in self._fields for f in ["mobile", "phone", "partner_id"]):
                    can_send = True

            store.add(
                self,
                {"canSendWhatsapp": can_send},
                as_thread=True,
            )

    def _whatsapp_get_channel(self, field_name, gateway):
        """
        Override to support relational fields like 'partner_id.mobile'.
        This allows WhatsApp integration to work with models that don't have
        direct phone fields but have them through relations.
        """
        # Get the phone number from the field (supports dot notation)
        phone_value = self._get_phone_value_from_field(field_name)

        if not phone_value:
            raise UserError(_("Phone number is not available for field %s") % field_name)

        # Format the phone number
        sanitized_number = self._phone_format(number=phone_value)
        if not sanitized_number:
            raise UserError(_("Phone cannot be sanitized"))

        # Avoid the plus sign prefix to match the whatsapp token
        sanitized_number = sanitized_number.replace("+", "")
        partner = self._whatsapp_get_partner()

        if not self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", partner.id),
                ("gateway_id", "=", gateway.id),
                ("gateway_token", "=", sanitized_number),
            ]
        ):
            self.env["res.partner.gateway.channel"].create(
                {
                    "name": gateway.name,
                    "partner_id": partner.id,
                    "gateway_id": gateway.id,
                    "gateway_token": sanitized_number,
                }
            )
        return self.env["mail.gateway.whatsapp"]._get_channel(
            gateway,
            sanitized_number,
            {
                "contacts": [
                    {
                        "wa_id": sanitized_number,
                        "profile": {"name": partner.display_name},
                    }
                ],
                "messages": [{"from": sanitized_number}],
            },
            force_create=True,
        )

    def _get_phone_value_from_field(self, field_name):
        """
        Get phone value from field name, supporting dot notation for relational fields.
        Examples:
        - 'mobile' -> direct field
        - 'partner_id.mobile' -> relational field
        - 'partner_id.phone' -> relational field
        """
        if not field_name:
            return False

        try:
            # Navigate through the field path
            value = self
            for field in field_name.split('.'):
                if not value:
                    return False
                value = value[field]

            return value if value else False
        except (KeyError, AttributeError):
            return False

