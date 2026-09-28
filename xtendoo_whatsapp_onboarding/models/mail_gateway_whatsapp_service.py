# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


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
        # Fall back to the wa_id (phone number) rather than an empty
        # string, so the channel still shows *something* identifiable
        # instead of a blank title.
        safe_update = dict(update)
        contacts = safe_update.get("contacts")
        if contacts:
            safe_update["contacts"] = [
                {
                    **contact,
                    "profile": contact.get("profile")
                    or {"name": contact.get("wa_id") or token},
                }
                for contact in contacts
            ]
        return super()._get_channel_vals(gateway, token, safe_update)

    def _process_update(self, chat, message, value):
        # mail_gateway_whatsapp._process_update() only extracts a body from
        # "text" or from a fixed set of media types (image/audio/video/
        # document/sticker) plus "location". Any other incoming message
        # type (button quick-reply, interactive reply, reaction, shared
        # contact...) silently ends up with an empty body, so the channel
        # gets created but no message is ever posted into it. Log the
        # message type/shape (never its content) so an empty-looking
        # conversation can be diagnosed from a real payload instead of
        # guessed at.
        handled_media = ("text", "image", "audio", "video", "document", "sticker", "location")
        if not any(message.get(key) for key in handled_media):
            _logger.warning(
                "[WhatsApp] Incoming message type not handled by "
                "_process_update, body will be empty: type=%s keys=%s "
                "(gateway=%s)",
                message.get("type"),
                list(message.keys()),
                chat.gateway_id.id,
            )
        return super()._process_update(chat, message, value)
