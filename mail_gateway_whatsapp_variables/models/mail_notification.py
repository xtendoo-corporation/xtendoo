# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
import logging
import requests
import requests_toolbelt

_logger = logging.getLogger(__name__)


class MailNotification(models.Model):
    _inherit = "mail.notification"

    def _send_gateway_notification(self):
        """
        Override to handle attachments with templates in WhatsApp.

        Strategy: Send template first, then send attachments as separate messages.
        This works because WhatsApp groups consecutive messages visually.
        """
        # Check if this is a WhatsApp notification with template and attachments
        if (
            self.gateway_channel_id
            and self.gateway_channel_id.gateway_id
            and self.gateway_channel_id.gateway_id.gateway_type == "whatsapp"
            and self.env.context.get("whatsapp_template_id")
            and self.mail_message_id.attachment_ids
        ):
            _logger.info(f"Processing WhatsApp notification with template and {len(self.mail_message_id.attachment_ids)} attachments")

            gateway = self.gateway_channel_id.gateway_id
            channel = self.gateway_channel_id

            # Temporarily store attachments and remove them
            original_attachments = self.mail_message_id.attachment_ids
            self.mail_message_id.attachment_ids = False

            try:
                # Send template message first (without attachments)
                result = super()._send_gateway_notification()

                # Now send each attachment as a separate message
                attachment_mimetype_map = self.env["mail.gateway.whatsapp"]._get_whatsapp_mimetype_kind()
                proxies = self.env["mail.gateway.whatsapp"]._get_proxies()

                for attachment in original_attachments:
                    if attachment.mimetype not in attachment_mimetype_map:
                        _logger.warning(f"Skipping attachment {attachment.name} - mimetype {attachment.mimetype} not supported")
                        continue

                    attachment_type = attachment_mimetype_map[attachment.mimetype]
                    _logger.info(f"Sending attachment: {attachment.name} (type: {attachment_type})")

                    try:
                        # Upload file to WhatsApp
                        m = requests_toolbelt.multipart.encoder.MultipartEncoder(
                            fields={
                                "file": (
                                    attachment.name,
                                    attachment.raw,
                                    attachment.mimetype,
                                ),
                                "messaging_product": "whatsapp",
                            },
                        )

                        upload_response = requests.post(
                            f"https://graph.facebook.com/"
                            f"v{gateway.whatsapp_version}/{gateway.whatsapp_from_phone}/media",
                            headers={
                                "Authorization": f"Bearer {gateway.token}",
                                "content-type": m.content_type,
                            },
                            data=m,
                            timeout=10,
                            proxies=proxies,
                        )
                        upload_response.raise_for_status()
                        media_id = upload_response.json()["id"]

                        _logger.info(f"Uploaded {attachment.name} to WhatsApp, media_id: {media_id}")

                        # Send the media message
                        media_payload = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": channel.gateway_channel_token,
                            "type": attachment_type,
                            attachment_type: {"id": media_id}
                        }

                        # Add filename for documents
                        if attachment_type == "document":
                            media_payload[attachment_type]["filename"] = attachment.name

                        send_response = requests.post(
                            f"https://graph.facebook.com/"
                            f"v{gateway.whatsapp_version}/{gateway.whatsapp_from_phone}/messages",
                            headers={"Authorization": f"Bearer {gateway.token}"},
                            json=media_payload,
                            timeout=10,
                            proxies=proxies,
                        )
                        send_response.raise_for_status()

                        _logger.info(f"Successfully sent attachment {attachment.name} via WhatsApp")

                    except Exception as att_error:
                        _logger.error(f"Error sending attachment {attachment.name}: {att_error}", exc_info=True)
                        # Continue with other attachments

                return result

            finally:
                # Always restore attachments
                self.mail_message_id.attachment_ids = original_attachments

        return super()._send_gateway_notification()

