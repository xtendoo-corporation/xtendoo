# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import uuid

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.facebook.com"
DEFAULT_GRAPH_VERSION = "21.0"
REQUEST_TIMEOUT = 20


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    # `token`, `webhook_key` and `whatsapp_security_key` are required (or
    # used to build the webhook URL) on the base/OCA models, which assume an
    # admin pastes in values obtained manually from Meta. For onboarding,
    # nobody should ever be asked to type a "Token" to create the record in
    # the first place: generate opaque placeholders automatically, and
    # action_save_meta_credentials() overwrites `token` with the real one
    # once Embedded Signup completes.
    token = fields.Char(default=lambda self: str(uuid.uuid4()))
    webhook_key = fields.Char(default=lambda self: str(uuid.uuid4()))
    whatsapp_security_key = fields.Char(default=lambda self: str(uuid.uuid4()))

    whatsapp_onboarding_state = fields.Selection(
        selection=[
            ("draft", "Not Connected"),
            ("connecting", "Connecting"),
            ("connected", "Connected"),
            ("error", "Error"),
            ("disconnected", "Disconnected"),
        ],
        string="WhatsApp Onboarding Status",
        default="draft",
        copy=False,
        readonly=True,
    )
    whatsapp_onboarding_session = fields.Char(copy=False, readonly=True)
    whatsapp_onboarding_business_id = fields.Char(
        string="Business Portfolio ID", copy=False, readonly=True
    )
    whatsapp_onboarding_phone_display = fields.Char(
        string="WhatsApp Number", copy=False, readonly=True
    )
    whatsapp_onboarding_connected_date = fields.Datetime(
        string="Connected On", copy=False, readonly=True
    )
    whatsapp_onboarding_last_sync_date = fields.Datetime(
        string="Last Sync", copy=False, readonly=True
    )
    whatsapp_onboarding_subscribed = fields.Boolean(
        string="Webhook Subscribed", copy=False, readonly=True
    )
    whatsapp_onboarding_last_error = fields.Text(copy=False, readonly=True)

    # ------------------------------------------------------------------
    # Entry point: "WhatsApp" menu
    # ------------------------------------------------------------------
    @api.model
    def action_get_or_create_whatsapp_gateway(self):
        """Single entry point behind the "WhatsApp" menu.

        The client should never have to fill in a technical form to reach
        the "Connect WhatsApp" button: this finds (or silently creates) the
        WhatsApp gateway for the current company and opens it directly.
        """
        gateway = self.search(
            [
                ("gateway_type", "=", "whatsapp"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if not gateway:
            gateway = self.create(
                {
                    "name": _("%s - WhatsApp") % self.env.company.name,
                    "gateway_type": "whatsapp",
                    "company_id": self.env.company.id,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.gateway",
            "res_id": gateway.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------
    def action_open_embedded_signup(self):
        self.ensure_one()
        if self.gateway_type != "whatsapp":
            raise UserError(
                _("Embedded Signup is only available for WhatsApp gateways.")
            )
        if not self.id:
            raise UserError(_("Save the gateway before connecting WhatsApp."))

        config = self._whatsapp_onboarding_get_meta_config()
        session = str(uuid.uuid4())
        self.write(
            {
                "whatsapp_onboarding_state": "connecting",
                "whatsapp_onboarding_session": session,
                "whatsapp_onboarding_last_error": False,
            }
        )
        _logger.info("[WhatsApp Onboarding] Inicio (gateway=%s)", self.id)
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_whatsapp_onboarding_embedded_signup",
            "params": {
                "gateway_id": self.id,
                "session": session,
                "app_id": config["app_id"],
                "config_id": config["config_id"],
                "graph_version": config["graph_version"],
            },
        }

    def action_reset_signup_attempt(self, session):
        """Called by the frontend when the user cancels the Meta popup."""
        self.ensure_one()
        if (
            session
            and session == self.whatsapp_onboarding_session
            and self.whatsapp_onboarding_state == "connecting"
        ):
            self.write({"whatsapp_onboarding_state": "draft"})
            _logger.info(
                "[WhatsApp Onboarding] Cancelado por el usuario (gateway=%s)", self.id
            )
        return True

    def action_save_meta_credentials(
        self, session, code, waba_id=False, phone_number_id=False, business_id=False
    ):
        """Backend handover: exchanges the Meta authorization code for a token,
        resolves the client's WABA/phone number and stores the connection.

        Called from the Embedded Signup client action once Meta has authorized
        Xtendoo's app. Never called with the App Secret or any token from JS.
        """
        self.ensure_one()
        if self.gateway_type != "whatsapp":
            raise UserError(_("The target gateway must be a WhatsApp gateway."))

        if not session or session != self.whatsapp_onboarding_session:
            _logger.info(
                "[WhatsApp Onboarding] Callback descartado por sesion obsoleta o "
                "duplicada (gateway=%s)",
                self.id,
            )
            return self._whatsapp_onboarding_notification(
                _(
                    'This connection attempt is no longer active. '
                    'Click "Connect WhatsApp" again.'
                ),
                warning=True,
            )

        if self.whatsapp_onboarding_state == "connected":
            _logger.info(
                "[WhatsApp Onboarding] Callback ignorado, gateway ya conectado "
                "(gateway=%s)",
                self.id,
            )
            return self._whatsapp_onboarding_notification(
                _("WhatsApp is already connected.")
            )

        if not code:
            self._whatsapp_onboarding_set_error(
                _("Meta did not return an authorization code.")
            )
            raise UserError(_("Meta did not return an authorization code."))

        config = self._whatsapp_onboarding_get_meta_config()
        try:
            _logger.info(
                "[WhatsApp Onboarding] Autorizacion recibida (gateway=%s)", self.id
            )
            token_payload = self._whatsapp_onboarding_exchange_code(code, config)
            access_token = token_payload.get("access_token")
            if not access_token:
                raise UserError(_("Meta did not return an access token."))

            resolved_waba_id = waba_id
            resolved_phone_id = phone_number_id
            resolved_business_id = business_id
            if not resolved_waba_id or not resolved_phone_id:
                fallback = self._whatsapp_onboarding_fetch_assets_fallback(
                    access_token, config
                )
                resolved_waba_id = resolved_waba_id or fallback.get("waba_id")
                resolved_phone_id = resolved_phone_id or fallback.get(
                    "phone_number_id"
                )
                resolved_business_id = resolved_business_id or fallback.get(
                    "business_id"
                )

            if not resolved_waba_id:
                raise UserError(
                    _("Meta did not return a WhatsApp Business Account.")
                )
            _logger.info("[WhatsApp Onboarding] WABA obtenida (gateway=%s)", self.id)

            if not resolved_phone_id:
                raise UserError(_("Meta did not return a WhatsApp phone number."))
            _logger.info(
                "[WhatsApp Onboarding] Phone Number obtenido (gateway=%s)", self.id
            )

            self._whatsapp_onboarding_check_not_duplicated(
                resolved_waba_id, resolved_phone_id
            )

            phone_info = {}
            try:
                phone_info = self._whatsapp_onboarding_fetch_phone_info(
                    resolved_phone_id, access_token, config
                )
            except Exception:
                _logger.info(
                    "[WhatsApp Onboarding] No se pudo obtener el nombre visible "
                    "del numero (gateway=%s)",
                    self.id,
                )

            self._whatsapp_onboarding_subscribe_app(
                resolved_waba_id, access_token, config
            )
            _logger.info(
                "[WhatsApp Onboarding] Webhook configurado (gateway=%s)", self.id
            )
            _logger.info("[WhatsApp Onboarding] Token procesado (gateway=%s)", self.id)

            self.write(
                {
                    "token": access_token,
                    "whatsapp_account_id": resolved_waba_id,
                    "whatsapp_from_phone": resolved_phone_id,
                    "whatsapp_onboarding_business_id": resolved_business_id,
                    "whatsapp_onboarding_phone_display": phone_info.get(
                        "display_phone_number"
                    ),
                    "whatsapp_onboarding_state": "connected",
                    "whatsapp_onboarding_connected_date": fields.Datetime.now(),
                    "whatsapp_onboarding_last_sync_date": fields.Datetime.now(),
                    "whatsapp_onboarding_subscribed": True,
                    "whatsapp_onboarding_last_error": False,
                }
            )
            _logger.info("[WhatsApp Onboarding] Completado (gateway=%s)", self.id)
        except Exception as err:
            self._whatsapp_onboarding_set_error(err)
            if isinstance(err, UserError):
                raise
            raise UserError(
                _("WhatsApp connection failed: %s")
                % self._whatsapp_onboarding_safe_message(err)
            ) from err

        return self._whatsapp_onboarding_notification(
            _("WhatsApp connected successfully.")
        )

    def action_resync(self):
        self.ensure_one()
        if self.whatsapp_onboarding_state != "connected":
            raise UserError(_("Connect WhatsApp before syncing."))
        config = self._whatsapp_onboarding_get_meta_config()
        try:
            phone_info = self._whatsapp_onboarding_fetch_phone_info(
                self.whatsapp_from_phone, self.token, config
            )
            self.write(
                {
                    "whatsapp_onboarding_phone_display": phone_info.get(
                        "display_phone_number"
                    )
                    or self.whatsapp_onboarding_phone_display,
                    "whatsapp_onboarding_last_sync_date": fields.Datetime.now(),
                    "whatsapp_onboarding_last_error": False,
                }
            )
            _logger.info("[WhatsApp Onboarding] Sincronizado (gateway=%s)", self.id)
        except Exception as err:
            self._whatsapp_onboarding_set_error(err)
            raise UserError(
                _("Unable to sync WhatsApp data from Meta: %s")
                % self._whatsapp_onboarding_safe_message(err)
            ) from err
        return True

    def action_disconnect(self):
        self.ensure_one()
        if self.whatsapp_onboarding_state != "connected":
            return True
        waba_id = self.whatsapp_account_id
        token = self.token
        if waba_id and token:
            try:
                self._whatsapp_onboarding_unsubscribe_app(waba_id, token)
            except Exception:
                _logger.warning(
                    "[WhatsApp Onboarding] No se pudo desuscribir la app de la "
                    "WABA en Meta (gateway=%s), se continua con la desconexion "
                    "local.",
                    self.id,
                )
        self.write(
            {
                "token": str(uuid.uuid4()),
                "whatsapp_account_id": False,
                "whatsapp_from_phone": False,
                "whatsapp_onboarding_state": "disconnected",
                "whatsapp_onboarding_business_id": False,
                "whatsapp_onboarding_phone_display": False,
                "whatsapp_onboarding_subscribed": False,
                "whatsapp_onboarding_last_error": False,
                "integrated_webhook_state": False,
            }
        )
        _logger.info("[WhatsApp Onboarding] Desconectado (gateway=%s)", self.id)
        return True

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def _whatsapp_onboarding_get_meta_config(self):
        icp = self.env["ir.config_parameter"].sudo()
        app_id = icp.get_param("xtendoo_whatsapp_onboarding.meta_app_id")
        app_secret = icp.get_param("xtendoo_whatsapp_onboarding.meta_app_secret")
        config_id = icp.get_param("xtendoo_whatsapp_onboarding.meta_config_id")
        graph_version = (
            icp.get_param("xtendoo_whatsapp_onboarding.meta_graph_version")
            or DEFAULT_GRAPH_VERSION
        )
        if not app_id or not app_secret or not config_id:
            raise UserError(
                _(
                    "WhatsApp Embedded Signup is not configured yet. Ask your "
                    "Xtendoo administrator to fill in the Meta App ID, App "
                    "Secret and Embedded Signup Configuration ID in Settings."
                )
            )
        return {
            "app_id": app_id,
            "app_secret": app_secret,
            "config_id": config_id,
            "graph_version": graph_version,
        }

    # ------------------------------------------------------------------
    # Meta Graph API calls (server-to-server only)
    # ------------------------------------------------------------------
    def _whatsapp_onboarding_graph_url(self, path, config):
        return f"{GRAPH_BASE_URL}/v{config['graph_version']}/{path}"

    def _whatsapp_onboarding_exchange_code(self, code, config):
        endpoint = self._whatsapp_onboarding_graph_url("oauth/access_token", config)
        response = requests.get(
            endpoint,
            params={
                "client_id": config["app_id"],
                "client_secret": config["app_secret"],
                "code": code,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def _whatsapp_onboarding_subscribe_app(self, waba_id, access_token, config):
        endpoint = self._whatsapp_onboarding_graph_url(
            f"{waba_id}/subscribed_apps", config
        )
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise UserError(
                _(
                    "Meta refused to subscribe the app to the WhatsApp "
                    "Business Account."
                )
            )
        return payload

    def _whatsapp_onboarding_unsubscribe_app(self, waba_id, access_token):
        config = self._whatsapp_onboarding_get_meta_config()
        endpoint = self._whatsapp_onboarding_graph_url(
            f"{waba_id}/subscribed_apps", config
        )
        response = requests.delete(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

    def _whatsapp_onboarding_fetch_phone_info(
        self, phone_number_id, access_token, config=None
    ):
        config = config or self._whatsapp_onboarding_get_meta_config()
        endpoint = self._whatsapp_onboarding_graph_url(phone_number_id, config)
        response = requests.get(
            endpoint,
            params={"fields": "display_phone_number,verified_name"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def _whatsapp_onboarding_fetch_assets_fallback(self, access_token, config):
        """Fallback only used when the frontend WA_EMBEDDED_SIGNUP postMessage
        did not carry the waba_id/phone_number_id (older SDK versions).
        """
        endpoint = self._whatsapp_onboarding_graph_url("me/businesses", config)
        response = requests.get(
            endpoint,
            params={
                "fields": (
                    "id,owned_whatsapp_business_accounts{id,phone_numbers{id}}"
                )
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        result = {"business_id": False, "waba_id": False, "phone_number_id": False}
        for business in payload.get("data", []):
            result["business_id"] = result["business_id"] or business.get("id")
            wabas = (business.get("owned_whatsapp_business_accounts") or {}).get(
                "data", []
            )
            for waba in wabas:
                result["waba_id"] = result["waba_id"] or waba.get("id")
                phones = (waba.get("phone_numbers") or {}).get("data", [])
                if phones:
                    result["phone_number_id"] = result["phone_number_id"] or phones[
                        0
                    ].get("id")
                if result["waba_id"] and result["phone_number_id"]:
                    return result
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _whatsapp_onboarding_check_not_duplicated(self, waba_id, phone_number_id):
        domain = [
            ("id", "!=", self.id),
            ("gateway_type", "=", "whatsapp"),
            ("whatsapp_onboarding_state", "=", "connected"),
            "|",
            ("whatsapp_account_id", "=", waba_id),
            ("whatsapp_from_phone", "=", phone_number_id),
        ]
        existing = self.sudo().search(domain, limit=1)
        if existing:
            raise UserError(
                _(
                    "This WhatsApp Business Account or phone number is "
                    "already connected to another Odoo gateway (%s)."
                )
                % existing.display_name
            )

    def _whatsapp_onboarding_set_error(self, err):
        """Persists the error state in its own DB transaction.

        The caller always re-raises after this (UserError), and Odoo rolls
        back the whole request's transaction on any uncaught exception. A
        plain `self.write(...)` here would therefore be silently undone
        together with the raise, leaving the gateway stuck without any
        visible error. Using a separate cursor (the same pattern `ir.cron`
        uses to log job failures) makes the error state survive regardless
        of what happens to the caller's transaction.
        """
        message = self._whatsapp_onboarding_safe_message(err)
        _logger.error(
            "[WhatsApp Onboarding] Error (gateway=%s): %s", self.id, message
        )
        gateway_id = self.id
        with self.env.registry.cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            new_env["mail.gateway"].browse(gateway_id).write(
                {
                    "whatsapp_onboarding_state": "error",
                    "whatsapp_onboarding_last_error": message,
                }
            )

    @staticmethod
    def _whatsapp_onboarding_safe_message(err):
        """Builds a log/UI-safe error message. Never includes tokens, the App
        Secret or authorization codes: only Meta's public error description
        (message/code), the HTTP status, or the exception type name.
        """
        if isinstance(err, requests.HTTPError) and err.response is not None:
            try:
                error_payload = err.response.json().get("error", {})
            except ValueError:
                error_payload = {}
            if error_payload.get("message"):
                return "%s (code %s)" % (
                    error_payload["message"],
                    error_payload.get("code"),
                )
            return _("Meta API returned HTTP %s") % err.response.status_code
        if isinstance(err, requests.RequestException):
            return _("Meta API request failed (%s)") % type(err).__name__
        if isinstance(err, UserError):
            return str(err)
        return str(err) or type(err).__name__

    def _whatsapp_onboarding_notification(self, message, warning=False):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Onboarding"),
                "message": message,
                "type": "warning" if warning else "success",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }
