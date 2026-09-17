# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Tests for xtendoo_whatsapp_webhook_relay (Odoo 18).

- HTTP controller tests (register/unregister) use HttpCase, real requests
  against the test server.
- _receive_update splitting/routing tests use TransactionCase directly;
  outbound relay HTTP calls are mocked, no real network access.
"""
import json
import uuid
from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, TransactionCase, tagged

RELAY_REQUESTS_TARGET = (
    "odoo.addons.xtendoo_whatsapp_webhook_relay.models.mail_gateway_whatsapp.requests"
)
API_KEY = "SECRET-RELAY-KEY-123"


@tagged("-at_install", "post_install")
class TestWhatsappRelayController(HttpCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_whatsapp_webhook_relay.api_key", API_KEY
        )

    def _post(self, path, payload, api_key=API_KEY):
        headers = {"Content-Type": "application/json"}
        if api_key is not None:
            headers["X-Xtendoo-Relay-Key"] = api_key
        return self.url_open(path, data=json.dumps(payload).encode(), headers=headers)

    def test_register_requires_valid_api_key(self):
        response = self._post(
            "/xtendoo_whatsapp_relay/register",
            {
                "phone_number_id": "ctrl-phone-1",
                "webhook_url": "https://client.example.com/gateway/whatsapp/k1/update",
                "webhook_secret": "client-secret-1",
            },
            api_key="WRONG-KEY",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            self.env["xtendoo.whatsapp.relay.client"]
            .sudo()
            .search([("phone_number_id", "=", "ctrl-phone-1")])
        )

    def test_register_requires_api_key_header(self):
        response = self._post(
            "/xtendoo_whatsapp_relay/register",
            {
                "phone_number_id": "ctrl-phone-1b",
                "webhook_url": "https://client.example.com/gateway/whatsapp/k1b/update",
                "webhook_secret": "s",
            },
            api_key=None,
        )
        self.assertEqual(response.status_code, 403)

    def test_register_missing_fields(self):
        response = self._post(
            "/xtendoo_whatsapp_relay/register", {"phone_number_id": "ctrl-phone-2"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            self.env["xtendoo.whatsapp.relay.client"]
            .sudo()
            .search([("phone_number_id", "=", "ctrl-phone-2")])
        )

    def test_register_creates_and_is_idempotent(self):
        payload = {
            "phone_number_id": "ctrl-phone-3",
            "waba_id": "waba-3",
            "name": "Client Three",
            "webhook_url": "https://client3.example.com/gateway/whatsapp/kX/update",
            "webhook_secret": "secret-3",
        }
        response = self._post("/xtendoo_whatsapp_relay/register", payload)
        self.assertEqual(response.status_code, 200)
        records = (
            self.env["xtendoo.whatsapp.relay.client"]
            .sudo()
            .search([("phone_number_id", "=", "ctrl-phone-3")])
        )
        self.assertEqual(len(records), 1)

        payload["webhook_secret"] = "secret-3-rotated"
        response = self._post("/xtendoo_whatsapp_relay/register", payload)
        self.assertEqual(response.status_code, 200)
        records = (
            self.env["xtendoo.whatsapp.relay.client"]
            .sudo()
            .search([("phone_number_id", "=", "ctrl-phone-3")])
        )
        self.assertEqual(len(records), 1, "registering twice must not duplicate")
        self.assertEqual(records.webhook_secret, "secret-3-rotated")

    def test_unregister_deactivates_without_deleting(self):
        self._post(
            "/xtendoo_whatsapp_relay/register",
            {
                "phone_number_id": "ctrl-phone-4",
                "webhook_url": "https://client4.example.com/gateway/whatsapp/kY/update",
                "webhook_secret": "secret-4",
            },
        )
        response = self._post(
            "/xtendoo_whatsapp_relay/unregister", {"phone_number_id": "ctrl-phone-4"}
        )
        self.assertEqual(response.status_code, 200)
        record = (
            self.env["xtendoo.whatsapp.relay.client"]
            .sudo()
            .with_context(active_test=False)
            .search([("phone_number_id", "=", "ctrl-phone-4")])
        )
        self.assertTrue(record, "record must still exist, only deactivated")
        self.assertFalse(record.active)


@tagged("-at_install", "post_install")
class TestWhatsappRelayReceive(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.own_gateway = cls.env["mail.gateway"].create(
            {
                "name": "Xtendoo Own Gateway",
                "gateway_type": "whatsapp",
                "token": str(uuid.uuid4()),
                "webhook_key": str(uuid.uuid4()),
                "webhook_secret": str(uuid.uuid4()),
                "whatsapp_security_key": str(uuid.uuid4()),
                "whatsapp_from_phone": "own-phone-id",
            }
        )
        cls.client = cls.env["xtendoo.whatsapp.relay.client"].create(
            {
                "name": "Registered Client",
                "phone_number_id": "client-phone-id",
                "waba_id": "client-waba-id",
                "webhook_url": "https://client.example.com/gateway/whatsapp/abc/update",
                "webhook_secret": "client-webhook-secret",
            }
        )

    @staticmethod
    def _change(phone_number_id, wa_id="34600000000"):
        return {
            "field": "messages",
            "value": {
                "metadata": {
                    "phone_number_id": phone_number_id,
                    "display_phone_number": "+1",
                },
                "contacts": [{"wa_id": wa_id, "profile": {"name": "Someone"}}],
                "messages": [
                    {
                        "from": wa_id,
                        "id": "wamid.TEST",
                        "type": "text",
                        "text": {"body": "hi"},
                    }
                ],
            },
        }

    def _payload(self, *phone_number_ids):
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry-1",
                    "changes": [self._change(pid) for pid in phone_number_ids],
                }
            ],
        }

    def test_own_number_processed_locally_not_relayed(self):
        Service = self.env.registry["mail.gateway.whatsapp"]
        with patch.object(Service, "_get_channel") as mock_get_channel, patch(
            RELAY_REQUESTS_TARGET
        ) as mock_requests:
            mock_get_channel.return_value = False
            self.env["mail.gateway.whatsapp"]._receive_update(
                self.own_gateway, self._payload("own-phone-id")
            )
            mock_get_channel.assert_called_once()
            mock_requests.post.assert_not_called()

    def test_registered_foreign_number_is_relayed_not_processed_locally(self):
        Service = self.env.registry["mail.gateway.whatsapp"]
        with patch.object(Service, "_get_channel") as mock_get_channel, patch(
            RELAY_REQUESTS_TARGET
        ) as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=200)
            mock_requests.post.return_value.raise_for_status.return_value = None
            self.env["mail.gateway.whatsapp"]._receive_update(
                self.own_gateway, self._payload("client-phone-id")
            )
            mock_get_channel.assert_not_called()
            mock_requests.post.assert_called_once()
            call = mock_requests.post.call_args
            self.assertEqual(call.args[0], self.client.webhook_url)
            self.assertTrue(
                call.kwargs["headers"]["x-hub-signature-256"].startswith("sha256=")
            )
            relayed_body = json.loads(call.kwargs["data"])
            relayed_phone_ids = {
                change["value"]["metadata"]["phone_number_id"]
                for entry in relayed_body["entry"]
                for change in entry["changes"]
            }
            self.assertEqual(relayed_phone_ids, {"client-phone-id"})

        self.client.invalidate_recordset()
        self.assertTrue(self.client.last_relay_date)
        self.assertFalse(self.client.last_relay_error)

    def test_unregistered_foreign_number_is_dropped_safely(self):
        Service = self.env.registry["mail.gateway.whatsapp"]
        with patch.object(Service, "_get_channel") as mock_get_channel, patch(
            RELAY_REQUESTS_TARGET
        ) as mock_requests:
            self.env["mail.gateway.whatsapp"]._receive_update(
                self.own_gateway, self._payload("unknown-phone-id")
            )
            mock_get_channel.assert_not_called()
            mock_requests.post.assert_not_called()

    def test_mixed_payload_splits_correctly_without_cross_leak(self):
        Service = self.env.registry["mail.gateway.whatsapp"]
        with patch.object(Service, "_get_channel") as mock_get_channel, patch(
            RELAY_REQUESTS_TARGET
        ) as mock_requests:
            mock_get_channel.return_value = False
            mock_requests.post.return_value = MagicMock(status_code=200)
            mock_requests.post.return_value.raise_for_status.return_value = None
            self.env["mail.gateway.whatsapp"]._receive_update(
                self.own_gateway,
                self._payload("own-phone-id", "client-phone-id", "unknown-phone-id"),
            )
            mock_get_channel.assert_called_once()
            mock_requests.post.assert_called_once()
            relayed_body = json.loads(mock_requests.post.call_args.kwargs["data"])
            relayed_phone_ids = {
                change["value"]["metadata"]["phone_number_id"]
                for entry in relayed_body["entry"]
                for change in entry["changes"]
            }
            self.assertEqual(
                relayed_phone_ids,
                {"client-phone-id"},
                "must relay only the registered client's own entries, "
                "never Xtendoo's own or an unknown number's",
            )
