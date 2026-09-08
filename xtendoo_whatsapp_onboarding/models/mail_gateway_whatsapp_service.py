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
