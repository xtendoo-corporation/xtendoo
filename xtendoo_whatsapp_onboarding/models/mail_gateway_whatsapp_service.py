# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _send(self, gateway, *args, **kwargs):
        # Prefer Xtendoo's central, non-expiring token (if configured) over
        # the client's own stored token when sending messages. See
        # mail.gateway._whatsapp_onboarding_effective_token().
        with gateway._whatsapp_onboarding_effective_token():
            return super()._send(gateway, *args, **kwargs)

    def _get_channel_vals(self, gateway, token, update):
        # mail_gateway_whatsapp._get_channel_vals() does
        # contact["profile"]["name"] unconditionally, but Meta's webhook
        # payload does not always include a "profile" key on a contacts[]
        # entry (e.g. incoming messages from a number Meta has no known
        # display name for yet). That raises an uncaught KeyError, which
        # bubbles up as an HTTP 500 to Meta and drops the message entirely.
        # Sanitize the payload before handing it to the OCA method instead
        # of patching mail_gateway_whatsapp itself: same lookup, defensive
        # shape, no behavior change when "profile" is actually present.
        safe_update = dict(update)
        contacts = safe_update.get("contacts")
        if contacts:
            safe_update["contacts"] = [
                {
                    **contact,
                    "profile": contact.get("profile") or {"name": ""},
                }
                for contact in contacts
            ]
        return super()._get_channel_vals(gateway, token, safe_update)
