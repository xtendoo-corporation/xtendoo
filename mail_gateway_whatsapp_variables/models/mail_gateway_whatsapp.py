# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import requests
import requests_toolbelt
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        """
        Override to handle attachments with templates.
        When using templates, send template first, then attachments separately.
        """
        # Check if we have a template with attachments
        has_template = bool(self.env.context.get("whatsapp_template_id"))
        has_attachments = bool(record.mail_message_id.attachment_ids)

        if has_template and has_attachments:
            _logger.info(
                "Sending WhatsApp with template and %s attachments",
                len(record.mail_message_id.attachment_ids),
            )

            # Store attachments temporarily
            original_attachments = record.mail_message_id.attachment_ids

            # Remove attachments temporarily to send template first
            record.mail_message_id.attachment_ids = False

            try:
                # Send template first (calls parent which will handle the template)
                _logger.info("STEP 1: Sending template message...")
                super()._send(
                    gateway,
                    record,
                    auto_commit=False,
                    raise_exception=raise_exception,
                    parse_mode=parse_mode,
                )
                _logger.info("STEP 1 COMPLETE: Template sent successfully")

                # IMPORTANT: Wait a moment before sending attachment
                # WhatsApp may throttle consecutive messages
                import time

                _logger.info("Waiting 2 seconds before sending attachment...")
                time.sleep(2)

                # Now send attachments separately
                _logger.info("STEP 2: Preparing to send attachments...")
                attachment_mimetype_map = self._get_whatsapp_mimetype_kind()
                proxies = self._get_proxies()
                channel = record.gateway_channel_id

                sent_attachments = 0
                failed_attachments = 0

                for idx, attachment in enumerate(original_attachments, 1):
                    _logger.info(
                        "Processing attachment %s/%s: %s",
                        idx,
                        len(original_attachments),
                        attachment.name,
                    )

                    if attachment.mimetype not in attachment_mimetype_map:
                        _logger.warning(
                            "Skipping attachment %s - unsupported mimetype: %s",
                            attachment.name,
                            attachment.mimetype,
                        )
                        continue

                    attachment_type = attachment_mimetype_map[attachment.mimetype]

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

                        # Send media message
                        media_payload = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": channel.gateway_channel_token,
                            "type": attachment_type,
                            attachment_type: {"id": media_id},
                        }

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

                        if send_response.status_code != 200:
                            _logger.error(
                                "WhatsApp API returned non-200 status: %s - %s",
                                send_response.status_code,
                                send_response.text,
                            )
                            failed_attachments += 1
                            continue

                        send_response.raise_for_status()
                        response_data = send_response.json()

                        if "error" in response_data:
                            _logger.error(
                                "WhatsApp API Error: %s", response_data["error"]
                            )
                            failed_attachments += 1
                            continue

                        if not response_data.get("messages"):
                            _logger.warning(
                                "No 'messages' in response: %s", response_data
                            )
                            failed_attachments += 1
                        else:
                            sent_attachments += 1
                            _logger.info(
                                "Successfully sent attachment %s via WhatsApp",
                                attachment.name,
                            )

                    except Exception as att_error:
                        _logger.error(
                            "Error sending attachment %s: %s",
                            attachment.name,
                            att_error,
                            exc_info=True,
                        )
                        failed_attachments += 1

                _logger.info(
                    "SUMMARY: Template SENT, Attachments sent: %s, failed: %s",
                    sent_attachments,
                    failed_attachments,
                )

                # Commit if requested
                if auto_commit:
                    self.env.cr.commit()  # pylint: disable=invalid-commit

            finally:
                # Always restore attachments to the message
                record.mail_message_id.attachment_ids = original_attachments

            return

        # No template or no attachments: use standard flow
        return super()._send(
            gateway,
            record,
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            parse_mode=parse_mode,
        )

    def _send_payload(
        self, channel, body=False, media_id=False, media_type=False, media_name=False
    ):
        """Override to add quick_reply button components support.

        OCA's prepare_value_to_send() now handles header/body variables and
        dynamic URL buttons. We only need to add quick_reply button payloads
        which OCA does not generate.
        """
        # Get the base payload from parent (OCA already resolves variables via
        # prepare_value_to_send)
        payload = super()._send_payload(
            channel,
            body=body,
            media_id=media_id,
            media_type=media_type,
            media_name=media_name,
        )

        # If it's a template message, add quick_reply button components
        if payload and payload.get("type") == "template" and body:
            whatsapp_template_id = self.env.context.get("whatsapp_template_id")

            if whatsapp_template_id:
                whatsapp_template = self.env["mail.whatsapp.template"].browse(
                    whatsapp_template_id
                )

                # Add quick_reply button components (OCA doesn't handle these)
                if whatsapp_template.button_ids:
                    quick_reply_buttons = whatsapp_template.button_ids.filtered(
                        lambda b: b.button_type == "quick_reply"
                    )
                    if quick_reply_buttons:
                        existing_components = payload.get("template", {}).get(
                            "components", []
                        )
                        for idx, button in enumerate(quick_reply_buttons):
                            existing_components.append(
                                {
                                    "type": "button",
                                    "sub_type": "quick_reply",
                                    "index": str(idx),
                                    "parameters": [
                                        {
                                            "type": "payload",
                                            "payload": button.name,
                                        }
                                    ],
                                }
                            )
                        payload["template"]["components"] = existing_components

        return payload

    def _process_update(self, chat, message, value):
        super()._process_update(chat, message, value)

        # Identify the destination partner of the conversation
        partner = None
        if hasattr(chat, "channel_partner_ids") and chat.channel_partner_ids:
            partners = chat.channel_partner_ids.filtered(
                lambda p: p.id != self.env.ref("base.partner_root").id
                and p.id != self.env.user.partner_id.id
            )
            if partners:
                partner = partners[0]

        # Detect button responses from WhatsApp (all known variants)
        button_text = None
        if message.get("type") == "button":
            button_text = message.get("button", {}).get("text")
        elif message.get("type") == "button_reply":
            button_text = message.get("button_reply", {}).get("title")
        elif message.get("type") == "interactive":
            button_text = (
                message.get("interactive", {}).get("button_reply", {}).get("title")
            )

        # Get text body from message
        body = ""
        if message.get("text"):
            body = message.get("text").get("body", "")

        # === Process pending confirmations ===
        # When a message is received (button or text), check for pending confirmations
        if partner and chat:
            try:
                _logger.info(
                    "Checking for pending confirmations for partner %s (ID: %s)",
                    partner.name,
                    partner.id,
                )

                # Search for pending confirmations for this partner and channel
                pending_confirmations = self.env[
                    "whatsapp.pending.confirmation"
                ].search(
                    [
                        ("partner_id", "=", partner.id),
                        ("channel_id", "=", chat.id),
                        ("state", "=", "waiting"),
                    ]
                )

                if pending_confirmations:
                    _logger.info(
                        "Found %s pending confirmation(s)",
                        len(pending_confirmations),
                    )

                    # Build message_data based on the received message type
                    message_data = {
                        "type": message.get("type", "text"),
                        "text": {"body": body} if body else {},
                    }

                    # If it's an interactive button, mark the correct type
                    if button_text:
                        message_data["type"] = "interactive"
                        message_data["interactive"] = {
                            "button_reply": {
                                "title": button_text,
                                "id": button_text,
                            }
                        }

                    # Process each pending confirmation
                    for pending in pending_confirmations:
                        _logger.info(
                            "Processing pending confirmation %s (template: %s)",
                            pending.id,
                            pending.template_id.name,
                        )
                        if pending.process_confirmation_response(message_data):
                            _logger.info(
                                "Confirmation %s processed successfully!",
                                pending.id,
                            )
                            break  # Only process one confirmation per message
                else:
                    _logger.info(
                        "No pending confirmations found for partner %s",
                        partner.name,
                    )

            except Exception as e:
                _logger.error(
                    "Error processing pending confirmations: %s",
                    e,
                    exc_info=True,
                )
