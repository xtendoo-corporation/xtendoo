# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hmac
import json
import logging

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class XtendooWhatsappRelayController(Controller):
    def _xtendoo_relay_check_api_key(self):
        provided = request.httprequest.headers.get("X-Xtendoo-Relay-Key") or ""
        expected = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_whatsapp_webhook_relay.api_key")
            or ""
        )
        # Never accept an empty expected key: an unconfigured relay must
        # reject every request, not accept requests with an empty header.
        return bool(expected) and hmac.compare_digest(provided, expected)

    def _xtendoo_relay_json_response(self, status_code, payload):
        response = request.make_response(
            json.dumps(payload), [("Content-Type", "application/json")]
        )
        response.status_code = status_code
        return response

    @route(
        "/xtendoo_whatsapp_relay/register",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def register(self, **kwargs):
        if not self._xtendoo_relay_check_api_key():
            return self._xtendoo_relay_json_response(403, {"error": "invalid_api_key"})
        try:
            body = json.loads(request.httprequest.get_data().decode("utf-8"))
        except ValueError:
            return self._xtendoo_relay_json_response(400, {"error": "invalid_json"})

        missing = [
            field
            for field in ("phone_number_id", "webhook_url", "webhook_secret")
            if not body.get(field)
        ]
        if missing:
            return self._xtendoo_relay_json_response(
                400, {"error": "missing_fields", "fields": missing}
            )

        record = request.env["xtendoo.whatsapp.relay.client"]._xtendoo_relay_register(
            body
        )
        return self._xtendoo_relay_json_response(200, {"ok": True, "id": record.id})

    @route(
        "/xtendoo_whatsapp_relay/unregister",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def unregister(self, **kwargs):
        if not self._xtendoo_relay_check_api_key():
            return self._xtendoo_relay_json_response(403, {"error": "invalid_api_key"})
        try:
            body = json.loads(request.httprequest.get_data().decode("utf-8"))
        except ValueError:
            return self._xtendoo_relay_json_response(400, {"error": "invalid_json"})

        phone_number_id = body.get("phone_number_id")
        if not phone_number_id:
            return self._xtendoo_relay_json_response(
                400, {"error": "missing_fields", "fields": ["phone_number_id"]}
            )

        found = request.env[
            "xtendoo.whatsapp.relay.client"
        ]._xtendoo_relay_unregister(phone_number_id)
        return self._xtendoo_relay_json_response(200, {"ok": True, "found": found})
