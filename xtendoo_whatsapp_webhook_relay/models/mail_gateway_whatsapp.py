# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
import logging

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15


class MailGatewayWhatsappRelay(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _receive_update(self, gateway, update):
        """Split an incoming Meta webhook payload by `phone_number_id`.

        Meta's app-level Callback URL is shared by every client onboarded
        via xtendoo_whatsapp_onboarding, so a single webhook call may (in
        theory) batch events for several different phone numbers. Anything
        addressed to this gateway's own number is processed exactly as
        before (unchanged OCA behavior). Anything addressed to a different,
        *registered* number is filtered out and relayed unmodified to that
        client's own webhook URL, signed with the client's own secret, so
        their existing (unmodified) mail_gateway_whatsapp accepts and
        processes it exactly as if Meta had called them directly. Unknown
        (unregistered) numbers are dropped and logged, never processed
        locally and never relayed anywhere.
        """
        if not update or not update.get("entry"):
            return super()._receive_update(gateway, update)

        own_entries = []
        foreign_entries_by_phone = {}

        for entry in update.get("entry", []):
            own_changes = []
            foreign_changes_by_phone = {}
            for change in entry.get("changes", []):
                phone_number_id = (
                    change.get("value", {}).get("metadata", {}).get("phone_number_id")
                )
                if not phone_number_id or phone_number_id == gateway.whatsapp_from_phone:
                    own_changes.append(change)
                else:
                    foreign_changes_by_phone.setdefault(phone_number_id, []).append(
                        change
                    )
            if own_changes:
                own_entries.append({**entry, "changes": own_changes})
            for phone_number_id, changes in foreign_changes_by_phone.items():
                foreign_entries_by_phone.setdefault(phone_number_id, []).append(
                    {**entry, "changes": changes}
                )

        result = None
        if own_entries:
            result = super()._receive_update(gateway, {**update, "entry": own_entries})

        for phone_number_id, entries in foreign_entries_by_phone.items():
            self._xtendoo_relay_forward(
                phone_number_id, {**update, "entry": entries}
            )

        return result

    def _xtendoo_relay_forward(self, phone_number_id, payload):
        client = (
            self.env["xtendoo.whatsapp.relay.client"]
            .sudo()
            .search(
                [("phone_number_id", "=", phone_number_id), ("active", "=", True)],
                limit=1,
            )
        )
        if not client:
            _logger.info(
                "[WhatsApp Relay] phone_number_id=%s no tiene ningun cliente "
                "registrado, se descarta el evento.",
                phone_number_id,
            )
            return

        body = json.dumps(payload, separators=(",", ":")).encode()
        signature = hmac.new(
            client.webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        try:
            response = requests.post(
                client.webhook_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-hub-signature-256": f"sha256={signature}",
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            client.sudo().write(
                {"last_relay_date": fields.Datetime.now(), "last_relay_error": False}
            )
            _logger.info(
                "[WhatsApp Relay] Reenviado a %s (phone_number_id=%s)",
                client.name,
                phone_number_id,
            )
        except Exception as err:
            _logger.error(
                "[WhatsApp Relay] Fallo al reenviar a %s (phone_number_id=%s): %s",
                client.name,
                phone_number_id,
                type(err).__name__,
            )
            client.sudo().write({"last_relay_error": type(err).__name__})
