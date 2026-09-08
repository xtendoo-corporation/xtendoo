# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Tests for xtendoo_whatsapp_onboarding (Odoo 18).

All Meta Graph API calls are mocked: no test depends on a real Meta/WhatsApp
account. Covers: onboarding start, valid/invalid callback, cancellation,
Meta errors, missing WABA/phone/token, expired token, retry, duplicates
(WABA and stale/duplicate callback), multi-company isolation, missing
permissions, disconnection and the full state machine.
"""
import uuid
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

REQUESTS_TARGET = "odoo.addons.xtendoo_whatsapp_onboarding.models.mail_gateway.requests"
LOGGER_NAME = "odoo.addons.xtendoo_whatsapp_onboarding.models.mail_gateway"
TEMPLATE_REQUESTS_TARGET = "odoo.addons.mail_gateway_whatsapp.models.mail_gateway.requests"


def _mock_response(json_data, status_code=200, raise_error=False):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    if raise_error:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    else:
        response.raise_for_status.return_value = None
    return response


@tagged("-at_install", "post_install")
class TestWhatsappOnboarding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        icp = cls.env["ir.config_parameter"].sudo()
        icp.set_param("xtendoo_whatsapp_onboarding.meta_app_id", "123456")
        icp.set_param("xtendoo_whatsapp_onboarding.meta_app_secret", "s3cr3t")
        icp.set_param("xtendoo_whatsapp_onboarding.meta_config_id", "cfg-1")
        icp.set_param("xtendoo_whatsapp_onboarding.meta_graph_version", "21.0")

        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Test WhatsApp Gateway",
                "gateway_type": "whatsapp",
                "token": str(uuid.uuid4()),
            }
        )

    def _start_signup(self, gateway=None):
        gateway = gateway or self.gateway
        action = gateway.action_open_embedded_signup()
        return action["params"]["session"]

    def _patch_graph(self, exchange=None, subscribe=None, phone=None, fallback=None):
        patcher = patch(REQUESTS_TARGET)
        mock_requests = patcher.start()
        self.addCleanup(patcher.stop)
        mock_requests.HTTPError = requests.HTTPError
        mock_requests.RequestException = requests.RequestException

        def get_side_effect(url, params=None, headers=None, timeout=None):
            if "oauth/access_token" in url:
                if exchange is None:
                    raise AssertionError("unexpected code exchange call")
                return exchange
            if "me/businesses" in url:
                return fallback or _mock_response({"data": []})
            return phone or _mock_response({"display_phone_number": "+34 600 000 000"})

        def post_side_effect(url, headers=None, timeout=None):
            if "subscribed_apps" in url:
                return subscribe or _mock_response({"success": True})
            raise AssertionError("unexpected POST call: %s" % url)

        mock_requests.get.side_effect = get_side_effect
        mock_requests.post.side_effect = post_side_effect
        return mock_requests

    # 1. Inicio del onboarding -------------------------------------------------
    def test_01_open_embedded_signup_starts_flow(self):
        session = self._start_signup()
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "connecting")
        self.assertTrue(session)
        self.assertEqual(self.gateway.whatsapp_onboarding_session, session)

    def test_01b_open_embedded_signup_without_config_raises(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_whatsapp_onboarding.meta_app_id", ""
        )
        with self.assertRaises(UserError):
            self.gateway.action_open_embedded_signup()

    # 2. Callback correcto -------------------------------------------------
    def test_02_save_meta_credentials_happy_path(self):
        session = self._start_signup()
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-ABC"}))
        with self.assertLogs(LOGGER_NAME, level="INFO") as log_ctx:
            self.gateway.action_save_meta_credentials(
                session, "auth-code", waba_id="waba-1", phone_number_id="phone-1"
            )
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "connected")
        self.assertEqual(self.gateway.whatsapp_account_id, "waba-1")
        self.assertEqual(self.gateway.whatsapp_from_phone, "phone-1")
        self.assertEqual(self.gateway.token, "TOKEN-ABC")
        self.assertTrue(self.gateway.whatsapp_onboarding_subscribed)
        for record in log_ctx.output:
            self.assertNotIn("TOKEN-ABC", record)
            self.assertNotIn("s3cr3t", record)

    # 3. Callback inválido (sin code) ---------------------------------------
    def test_03_save_meta_credentials_invalid_code(self):
        # NOTE: the error state is persisted through a separate cursor (see
        # _whatsapp_onboarding_set_error) so that it survives the rollback
        # Odoo performs on the calling transaction after an uncaught
        # exception. TransactionCase.assertRaises itself rolls back to a
        # savepoint on match, and the gateway row only exists inside the
        # still-open, never-committed outer test transaction, so a second
        # cursor cannot see it either way: persistence across the rollback
        # isn't observable from here. We only assert the user-facing
        # behavior (a clean UserError, not a crash).
        session = self._start_signup()
        with self.assertRaises(UserError):
            self.gateway.action_save_meta_credentials(session, False)

    # 4. Usuario cancela -----------------------------------------------------
    def test_04_user_cancels_resets_to_draft(self):
        session = self._start_signup()
        self.gateway.action_reset_signup_attempt(session)
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "draft")

    # 5. Error de Meta (HTTP error al intercambiar el code) ------------------
    def test_05_meta_http_error_on_exchange(self):
        session = self._start_signup()
        self._patch_graph(
            exchange=_mock_response(
                {"error": {"message": "Invalid code", "code": 100}},
                status_code=400,
                raise_error=True,
            )
        )
        with self.assertRaises(UserError) as ctx:
            self.gateway.action_save_meta_credentials(session, "bad-code")
        self.assertIn("Invalid code", str(ctx.exception))

    # 6. WABA no encontrada ----------------------------------------------
    def test_06_waba_not_found(self):
        session = self._start_signup()
        self._patch_graph(
            exchange=_mock_response({"access_token": "TOKEN-X"}),
            fallback=_mock_response({"data": []}),
        )
        with self.assertRaises(UserError) as ctx:
            self.gateway.action_save_meta_credentials(session, "auth-code")
        self.assertIn("WhatsApp Business Account", str(ctx.exception))

    # 7. Phone Number no encontrado ------------------------------------------
    def test_07_phone_number_not_found(self):
        session = self._start_signup()
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-X"}))
        with self.assertRaises(UserError) as ctx:
            self.gateway.action_save_meta_credentials(
                session, "auth-code", waba_id="waba-1"
            )
        self.assertIn("phone number", str(ctx.exception))

    # 8. Token inválido (Meta no devuelve access_token) ----------------------
    def test_08_missing_access_token(self):
        session = self._start_signup()
        self._patch_graph(exchange=_mock_response({}))
        with self.assertRaises(UserError) as ctx:
            self.gateway.action_save_meta_credentials(session, "auth-code")
        self.assertIn("access token", str(ctx.exception))

    # 9. Token expirado (resync falla) ---------------------------------------
    def test_09_resync_with_expired_token(self):
        session = self._start_signup()
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-X"}))
        self.gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-1", phone_number_id="phone-1"
        )
        self._patch_graph(
            phone=_mock_response(
                {"error": {"message": "Error validating access token", "code": 190}},
                status_code=401,
                raise_error=True,
            ),
        )
        with self.assertRaises(UserError):
            self.gateway.action_resync()

    # 10. Reintento tras error ------------------------------------------------
    def test_10_retry_after_error_generates_new_session(self):
        session = self._start_signup()
        with self.assertRaises(UserError):
            self.gateway.action_save_meta_credentials(session, False)
        new_session = self._start_signup()
        self.assertNotEqual(session, new_session)
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "connecting")

    # 11. Duplicados: WABA ya conectada a otro gateway -----------------------
    def test_11_duplicate_waba_rejected(self):
        session = self._start_signup()
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-1"}))
        self.gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-shared", phone_number_id="phone-1"
        )

        other_gateway = self.env["mail.gateway"].create(
            {
                "name": "Other Gateway",
                "gateway_type": "whatsapp",
                "token": str(uuid.uuid4()),
            }
        )
        other_session = self._start_signup(other_gateway)
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-2"}))
        with self.assertRaises(UserError) as ctx:
            other_gateway.action_save_meta_credentials(
                other_session,
                "auth-code",
                waba_id="waba-shared",
                phone_number_id="phone-2",
            )
        self.assertIn("already connected", str(ctx.exception))

    # 11b. Duplicados: callback duplicado / sesión obsoleta se ignora --------
    def test_11b_stale_session_is_ignored(self):
        self._start_signup()
        result = self.gateway.action_save_meta_credentials(
            "stale-session-id",
            "auth-code",
            waba_id="waba-1",
            phone_number_id="phone-1",
        )
        self.assertEqual(result["params"]["type"], "warning")
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "connecting")

    # 11c. Callback ignorado si ya está conectado (idempotencia) -------------
    def test_11c_already_connected_is_idempotent(self):
        session = self._start_signup()
        mock_requests = self._patch_graph(
            exchange=_mock_response({"access_token": "TOKEN-1"})
        )
        self.gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-1", phone_number_id="phone-1"
        )
        mock_requests.get.reset_mock()
        mock_requests.post.reset_mock()
        result = self.gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-1", phone_number_id="phone-1"
        )
        self.assertEqual(result["params"]["type"], "success")
        mock_requests.get.assert_not_called()
        mock_requests.post.assert_not_called()

    # 12. Multi-company: una empresa no puede ver el gateway de otra ---------
    def test_12_multi_company_isolation(self):
        company_b = self.env["res.company"].create({"name": "Company B"})
        gateway_b = self.env["mail.gateway"].create(
            {
                "name": "Gateway Company B",
                "gateway_type": "whatsapp",
                "token": str(uuid.uuid4()),
                "company_id": company_b.id,
            }
        )
        user_a = self.env["res.users"].create(
            {
                "name": "User Company A",
                "login": "user_company_a_whatsapp",
                "email": "user_company_a_whatsapp@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_system").id])],
                "company_ids": [(6, 0, [self.env.ref("base.main_company").id])],
                "company_id": self.env.ref("base.main_company").id,
            }
        )
        with self.assertRaises(AccessError):
            gateway_b.with_user(user_a).read(["name"])

    # 13. Usuario sin permisos -------------------------------------------
    def test_13_user_without_access_group(self):
        # mail_gateway grants read-only access to plain internal users by
        # design (access_mail_gateway_user, perm_write=0). A user with only
        # base.group_user can therefore see the gateway exists, but must not
        # be able to write to it or start/complete the onboarding flow.
        plain_user = self.env["res.users"].create(
            {
                "name": "Plain Internal User",
                "login": "plain_user_whatsapp",
                "email": "plain_user_whatsapp@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.gateway.with_user(plain_user).write({"name": "Hacked"})
        with self.assertRaises(AccessError):
            self.gateway.with_user(plain_user).action_open_embedded_signup()

    # 14. Desconexión --------------------------------------------------------
    def test_14_disconnect_clears_credentials(self):
        session = self._start_signup()
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-1"}))
        self.gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-1", phone_number_id="phone-1"
        )
        self._patch_graph()
        self.gateway.action_disconnect()
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "disconnected")
        self.assertFalse(self.gateway.whatsapp_account_id)
        self.assertFalse(self.gateway.whatsapp_from_phone)
        self.assertNotEqual(self.gateway.token, "TOKEN-1")

    # 15. Estados del proceso (transición completa) --------------------------
    def test_15_full_state_transition(self):
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "draft")
        session = self._start_signup()
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "connecting")
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-1"}))
        self.gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-1", phone_number_id="phone-1"
        )
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "connected")
        self._patch_graph()
        self.gateway.action_disconnect()
        self.assertEqual(self.gateway.whatsapp_onboarding_state, "disconnected")

    # 16. Zero-touch creation: no manual token/webhook data required --------
    def test_16_gateway_creation_requires_no_technical_input(self):
        # `token` is required on the base mail.gateway model (a plain admin
        # form would otherwise force typing a fake "Token" before the
        # Connect WhatsApp button is even reachable). Confirm it's now
        # auto-generated instead.
        gateway = self.env["mail.gateway"].create(
            {"name": "Zero Touch Co - WhatsApp", "gateway_type": "whatsapp"}
        )
        self.assertTrue(gateway.token)
        self.assertTrue(gateway.webhook_key)
        self.assertTrue(gateway.whatsapp_security_key)
        self.assertEqual(gateway.whatsapp_onboarding_state, "draft")

    # 16b. "WhatsApp" menu: single entry point, no list, no create form -----
    def test_16b_get_or_create_is_idempotent_per_company(self):
        # A fresh company with no WhatsApp gateway yet: the first call must
        # create exactly one, the second call must reuse it (no duplicate).
        Gateway = self.env["mail.gateway"]
        new_company = self.env["res.company"].create({"name": "Fresh Co"})
        result_1 = Gateway.with_company(new_company).action_get_or_create_whatsapp_gateway()
        result_2 = Gateway.with_company(new_company).action_get_or_create_whatsapp_gateway()
        count = Gateway.search_count(
            [
                ("gateway_type", "=", "whatsapp"),
                ("company_id", "=", new_company.id),
            ]
        )
        self.assertEqual(count, 1)
        self.assertEqual(result_1["res_id"], result_2["res_id"])

        # A company that already has one (setUpClass's self.gateway, or any
        # other pre-existing whatsapp gateway for the default company) must
        # never get a second one created.
        before_count = Gateway.search_count(
            [
                ("gateway_type", "=", "whatsapp"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        existing_result = Gateway.action_get_or_create_whatsapp_gateway()
        after_count = Gateway.search_count(
            [
                ("gateway_type", "=", "whatsapp"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        self.assertEqual(after_count, before_count)
        self.assertIn(
            existing_result["res_id"],
            Gateway.search(
                [
                    ("gateway_type", "=", "whatsapp"),
                    ("company_id", "=", self.env.company.id),
                ]
            ).ids,
        )

    # 17. Central Xtendoo System User token preferred over the client's own -
    def _connect_gateway(self, gateway=None, token="TOKEN-CLIENT-1"):
        gateway = gateway or self.gateway
        session = self._start_signup(gateway)
        self._patch_graph(exchange=_mock_response({"access_token": token}))
        gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-central-test", phone_number_id="phone-1"
        )
        return gateway

    def test_17_central_token_used_for_template_import_when_configured(self):
        self._connect_gateway()
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_whatsapp_onboarding.meta_system_user_token", "CENTRAL-TOKEN-XYZ"
        )
        with patch(TEMPLATE_REQUESTS_TARGET) as mock_requests:
            mock_requests.get.return_value = _mock_response({"data": []})
            self.gateway.button_import_whatsapp_template()
            used_headers = mock_requests.get.call_args.kwargs["headers"]
            self.assertEqual(used_headers["Authorization"], "Bearer CENTRAL-TOKEN-XYZ")

        # The per-client token stored in the DB must be untouched: the
        # unique(token) SQL constraint means the shared central token can
        # never be written into more than one gateway's `token` column.
        self.assertEqual(self.gateway.token, "TOKEN-CLIENT-1")

    def test_17b_client_token_used_when_no_central_token_configured(self):
        self._connect_gateway()
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_whatsapp_onboarding.meta_system_user_token", ""
        )
        with patch(TEMPLATE_REQUESTS_TARGET) as mock_requests:
            mock_requests.get.return_value = _mock_response({"data": []})
            self.gateway.button_import_whatsapp_template()
            used_headers = mock_requests.get.call_args.kwargs["headers"]
            self.assertEqual(used_headers["Authorization"], "Bearer TOKEN-CLIENT-1")

    def test_17c_central_token_does_not_break_uniqueness_across_clients(self):
        # Two different clients connected while a central token is
        # configured must still end up with two distinct, valid `token`
        # values in the DB (each client's own), never the same shared one.
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_whatsapp_onboarding.meta_system_user_token", "CENTRAL-TOKEN-XYZ"
        )
        self._connect_gateway(token="TOKEN-CLIENT-1")
        other_gateway = self.env["mail.gateway"].create(
            {"name": "Other Client - WhatsApp", "gateway_type": "whatsapp"}
        )
        session = self._start_signup(other_gateway)
        self._patch_graph(exchange=_mock_response({"access_token": "TOKEN-CLIENT-2"}))
        other_gateway.action_save_meta_credentials(
            session, "auth-code", waba_id="waba-other", phone_number_id="phone-other"
        )
        self.assertEqual(self.gateway.token, "TOKEN-CLIENT-1")
        self.assertEqual(other_gateway.token, "TOKEN-CLIENT-2")
        self.assertNotEqual(self.gateway.token, other_gateway.token)
