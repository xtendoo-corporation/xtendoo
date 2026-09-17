# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class XtendooWhatsappRelayClient(models.Model):
    _name = "xtendoo.whatsapp.relay.client"
    _description = "WhatsApp Webhook Relay - Registered Client"
    _rec_name = "name"

    name = fields.Char(
        required=True,
        help="Client display name, for admin reference only.",
    )
    phone_number_id = fields.Char(required=True, index=True)
    waba_id = fields.Char(string="WABA ID")
    webhook_url = fields.Char(
        required=True,
        string="Client Webhook URL",
        help="Full webhook URL of the client's own mail.gateway.",
    )
    webhook_secret = fields.Char(
        required=True,
        help=(
            "The client's own mail.gateway webhook_secret. Used to sign "
            "(HMAC-SHA256) relayed payloads exactly as Meta would, so the "
            "client's existing, unmodified webhook verification accepts them."
        ),
    )
    active = fields.Boolean(default=True)
    registered_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    last_relay_date = fields.Datetime(readonly=True, copy=False)
    last_relay_error = fields.Text(readonly=True, copy=False)

    _sql_constraints = [
        (
            "phone_number_id_uniq",
            "unique(phone_number_id)",
            "This phone number is already registered with another client.",
        ),
    ]

    def _xtendoo_relay_register(self, vals):
        """Create or update the registration for `vals['phone_number_id']`.
        Called only from the relay controller, after API key validation.
        """
        phone_number_id = vals.get("phone_number_id")
        record = self.sudo().search(
            [("phone_number_id", "=", phone_number_id)], limit=1
        )
        write_vals = {
            "name": vals.get("name") or phone_number_id,
            "phone_number_id": phone_number_id,
            "waba_id": vals.get("waba_id"),
            "webhook_url": vals.get("webhook_url"),
            "webhook_secret": vals.get("webhook_secret"),
            "active": True,
        }
        if record:
            record.write(write_vals)
        else:
            record = self.sudo().create(write_vals)
        _logger.info(
            "[WhatsApp Relay] Cliente registrado: %s (phone_number_id=%s)",
            record.name,
            phone_number_id,
        )
        return record

    def _xtendoo_relay_unregister(self, phone_number_id):
        record = self.sudo().search(
            [("phone_number_id", "=", phone_number_id)], limit=1
        )
        if record:
            record.write({"active": False})
            _logger.info(
                "[WhatsApp Relay] Cliente dado de baja: %s (phone_number_id=%s)",
                record.name,
                phone_number_id,
            )
        return bool(record)
