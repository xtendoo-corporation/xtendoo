# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.addons.mail.tools.discuss import Store


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

