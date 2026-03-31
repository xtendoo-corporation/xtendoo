# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_GRAPH_URL = "https://graph.facebook.com"
DEFAULT_GRAPH_VERSION = "21.0"


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    xtendoo_meta_app_id = fields.Char("Meta App ID")
    xtendoo_meta_config_id = fields.Char("Meta Config ID (Embedded Signup)")
    xtendoo_meta_app_secret = fields.Char("Meta App Secret")
    xtendoo_meta_business_id = fields.Char("Meta Business ID", copy=False, readonly=True)
    xtendoo_meta_waba_id = fields.Char("Meta WABA ID", copy=False, readonly=True)
    xtendoo_meta_phone_number_id = fields.Char(
        "Meta Phone Number ID", copy=False, readonly=True
    )
    xtendoo_meta_phone_number = fields.Char(
        "Meta Display Phone", copy=False, readonly=True
    )
    xtendoo_meta_signup_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("signup_started", "Signup Started"),
            ("authorized", "Authorized"),
            ("credentials_received", "Credentials Received"),
            ("error", "Error"),
        ],
        default="draft",
        copy=False,
        readonly=True,
        string="Meta Signup State",
    )
    xtendoo_meta_last_response = fields.Text("Meta Last Response", copy=False, readonly=True)
    xtendoo_meta_last_error = fields.Text("Meta Last Error", copy=False, readonly=True)

    def action_open_embedded_signup(self):
        self.ensure_one()
        if self.gateway_type != "whatsapp":
            raise UserError(_("The Embedded Signup flow is only available for WhatsApp gateways."))
        if not self.id:
            raise UserError(_("Please save the gateway before starting the Meta flow."))
        if not self.xtendoo_meta_app_id or not self.xtendoo_meta_config_id:
            raise UserError(_("Please fill in Meta App ID and Meta Config ID first."))
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_whatsapp_embedded_signup",
            "params": {
                "object_id": self.id,
                "call_model": "mail.gateway",
                "call_method": "action_save_meta_credentials",
                "app_id": self.xtendoo_meta_app_id,
                "config_id": self.xtendoo_meta_config_id,
                "graph_version": self._get_xtendoo_graph_version(),
                "gateway_name": self.display_name,
            },
        }

    def action_save_meta_credentials(self, code):
        self.ensure_one()
        if self.gateway_type != "whatsapp":
            raise UserError(_("The target gateway must be a WhatsApp gateway."))
        if not code:
            raise UserError(_("Meta did not return an authorization code."))
        if not self.xtendoo_meta_app_id:
            raise UserError(_("Meta App ID is required."))
        if not self.xtendoo_meta_app_secret:
            raise UserError(
                _(
                    "Meta App Secret is required to exchange the authorization code "
                    "for a permanent token."
                )
            )

        self.write(
            {
                "xtendoo_meta_signup_state": "signup_started",
                "xtendoo_meta_last_error": False,
            }
        )

        try:
            token_payload = self._xtendoo_exchange_meta_code(code)
            access_token = token_payload.get("access_token")
            if not access_token:
                raise UserError(_("Meta did not return an access token."))

            meta_payload = self._xtendoo_fetch_meta_payload(access_token)
            extracted = self._xtendoo_extract_whatsapp_assets(meta_payload)
            state = "authorized"
            if extracted.get("waba_id") or extracted.get("phone_number_id"):
                state = "credentials_received"

            write_vals = {
                "token": access_token,
                "xtendoo_meta_signup_state": state,
                "xtendoo_meta_last_error": False,
                "xtendoo_meta_last_response": json.dumps(
                    {
                        "oauth": token_payload,
                        "meta_payload": meta_payload,
                        "extracted": extracted,
                    },
                    indent=2,
                    sort_keys=True,
                ),
            }
            if extracted.get("business_id"):
                write_vals["xtendoo_meta_business_id"] = extracted["business_id"]
            if extracted.get("waba_id"):
                write_vals["xtendoo_meta_waba_id"] = extracted["waba_id"]
                write_vals["whatsapp_account_id"] = extracted["waba_id"]
            if extracted.get("phone_number_id"):
                write_vals["xtendoo_meta_phone_number_id"] = extracted["phone_number_id"]
                write_vals["whatsapp_from_phone"] = extracted["phone_number_id"]
            if extracted.get("display_phone_number"):
                write_vals["xtendoo_meta_phone_number"] = extracted[
                    "display_phone_number"
                ]

            self.write(write_vals)
        except Exception as err:
            error_message = str(err)
            _logger.exception("Meta Embedded Signup failed for gateway %s", self.id)
            self.write(
                {
                    "xtendoo_meta_signup_state": "error",
                    "xtendoo_meta_last_error": error_message,
                }
            )
            if isinstance(err, UserError):
                raise
            raise UserError(error_message) from err

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Embedded Signup"),
                "message": _(
                    "Meta credentials were saved on the gateway. Review the fetched IDs "
                    "and configure the webhook if needed."
                ),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _get_xtendoo_graph_version(self):
        self.ensure_one()
        version = (self.whatsapp_version or DEFAULT_GRAPH_VERSION).strip()
        return version[1:] if version.startswith("v") else version

    def _xtendoo_exchange_meta_code(self, code):
        self.ensure_one()
        endpoint = f"{BASE_GRAPH_URL}/v{self._get_xtendoo_graph_version()}/oauth/access_token"
        response = requests.get(
            endpoint,
            params={
                "client_id": self.xtendoo_meta_app_id,
                "client_secret": self.xtendoo_meta_app_secret,
                "code": code,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _xtendoo_fetch_meta_payload(self, access_token):
        self.ensure_one()
        headers = {"Authorization": f"Bearer {access_token}"}
        base_url = f"{BASE_GRAPH_URL}/v{self._get_xtendoo_graph_version()}"
        candidate_requests = [
            (
                f"{base_url}/me",
                {
                    "fields": (
                        "id,name,businesses{id,name,owned_whatsapp_business_accounts"
                        "{id,name,phone_numbers{id,display_phone_number,verified_name}}}"
                    )
                },
            ),
            (
                f"{base_url}/me/businesses",
                {
                    "fields": (
                        "id,name,owned_whatsapp_business_accounts"
                        "{id,name,phone_numbers{id,display_phone_number,verified_name}}"
                    )
                },
            ),
        ]
        collected = {}
        last_error = None
        for url, params in candidate_requests:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=20)
                response.raise_for_status()
                payload = response.json()
                if payload:
                    collected[url] = payload
            except requests.RequestException as err:
                last_error = err
                _logger.info("Meta Graph request failed for %s: %s", url, err)
        if not collected and last_error:
            raise UserError(_("Unable to fetch WhatsApp assets from Meta: %s") % last_error)
        return collected or {"token_only": {"access_token": access_token}}

    def _xtendoo_extract_whatsapp_assets(self, meta_payload):
        extracted = {
            "business_id": False,
            "waba_id": False,
            "phone_number_id": False,
            "display_phone_number": False,
        }
        payloads = meta_payload.values() if isinstance(meta_payload, dict) else [meta_payload]
        for payload in payloads:
            business_candidates = []
            if isinstance(payload, dict):
                business_candidates.extend(self._xtendoo_as_data_list(payload.get("businesses")))
                if payload.get("data") and isinstance(payload.get("data"), list):
                    business_candidates.extend(payload["data"])
                if payload.get("owned_whatsapp_business_accounts") or payload.get("phone_numbers"):
                    business_candidates.append(payload)
            for business in business_candidates:
                self._xtendoo_update_extracted_from_business(extracted, business)
                if extracted["waba_id"] and extracted["phone_number_id"]:
                    return extracted
        return extracted

    def _xtendoo_update_extracted_from_business(self, extracted, business):
        if not isinstance(business, dict):
            return
        extracted["business_id"] = extracted["business_id"] or business.get("id")
        waba_candidates = self._xtendoo_as_data_list(
            business.get("owned_whatsapp_business_accounts")
            or business.get("whatsapp_business_accounts")
        )
        if not waba_candidates and business.get("phone_numbers"):
            waba_candidates = [business]
        for waba in waba_candidates:
            if not isinstance(waba, dict):
                continue
            extracted["waba_id"] = extracted["waba_id"] or waba.get("id")
            phone_candidates = self._xtendoo_as_data_list(waba.get("phone_numbers"))
            for phone in phone_candidates:
                if not isinstance(phone, dict):
                    continue
                extracted["phone_number_id"] = extracted["phone_number_id"] or phone.get(
                    "id"
                )
                extracted["display_phone_number"] = extracted[
                    "display_phone_number"
                ] or phone.get("display_phone_number")
                if extracted["phone_number_id"]:
                    break
            if extracted["phone_number_id"]:
                break

    @staticmethod
    def _xtendoo_as_data_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict) and isinstance(value.get("data"), list):
            return value["data"]
        if isinstance(value, dict):
            return [value]
        return []

