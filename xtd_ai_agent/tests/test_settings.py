import json
from unittest.mock import patch

import requests

from odoo import tools
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from .test_provider_anthropic import FakeResponse, HttpMock, message_json

KEY = "sk-ant-api03-ADMINSECRET"
PARAM = "xtd_ai_agent.anthropic_api_key"


@tagged("post_install", "-at_install")
class TestAgentSettings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = new_test_user(cls.env, "xtd_ai_sysadm", groups="base.group_system")
        cls.config = cls.env["xtd.ai.agent.config"]
        cls.icp = cls.env["ir.config_parameter"].sudo()

    def setUp(self):
        super().setUp()
        patcher = patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.icp.set_param(PARAM, False)

    def settings(self, **vals):
        return self.env["res.config.settings"].with_user(self.admin).create(vals)

    # -- key ---------------------------------------------------------------
    def test_defaults(self):
        s = self.config._xtd_ai_provider_settings()
        self.assertEqual(
            (s.provider, s.model, s.effort, s.timeout),
            ("anthropic", "claude-haiku-5-5", "low", 30.0),
        )
        self.assertFalse(s.log_error_details)

    def test_key_is_stored_never_returned(self):
        record = self.settings(xtd_ai_agent_api_key_input=KEY)
        self.assertEqual(self.icp.get_param(PARAM), KEY)
        self.assertFalse(record.xtd_ai_agent_api_key_input)
        self.assertEqual(
            record.read(["xtd_ai_agent_api_key_input"])[0][
                "xtd_ai_agent_api_key_input"
            ],
            False,
        )
        self.assertTrue(record.xtd_ai_agent_api_key_set)
        self.assertFalse(record.xtd_ai_agent_api_key_env)
        values = (
            self.env["res.config.settings"]
            .with_user(self.admin)
            .default_get(list(self.env["res.config.settings"]._fields))
        )
        self.assertNotIn(KEY, json.dumps(values, default=str))
        # nor in the transient table
        self.env.cr.execute("SELECT row_to_json(t)::text FROM res_config_settings t")
        self.assertNotIn(KEY, " ".join(r[0] for r in self.env.cr.fetchall()))

    def test_empty_input_keeps_the_stored_key(self):
        self.icp.set_param(PARAM, KEY)
        self.settings(xtd_ai_agent_api_key_input="")
        self.assertEqual(self.icp.get_param(PARAM), KEY)

    def test_env_key_wins(self):
        self.icp.set_param(PARAM, KEY)
        self.assertEqual(self.config._xtd_ai_api_key(), KEY)
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-from-env"}):
            self.assertEqual(self.config._xtd_ai_api_key(), "sk-ant-from-env")
            state = self.config._xtd_ai_api_key_state()
            self.assertEqual(state, {"set": True, "from_env": True})

    def test_non_admin_cannot_set_or_clear_key(self):
        user = new_test_user(self.env, "xtd_ai_notadm", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["res.config.settings"].with_user(user).create(
                {"xtd_ai_agent_api_key_input": KEY}
            )
        self.assertFalse(self.icp.get_param(PARAM))
        with self.assertRaises(AccessError):
            self.config.with_user(user)._xtd_ai_test_connection()

    def test_clear_key(self):
        self.icp.set_param(PARAM, KEY)
        self.settings().action_xtd_ai_agent_clear_key()
        self.assertFalse(self.icp.get_param(PARAM))

    def test_config_error_without_key(self):
        self.assertIn("Ajustes → Agente IA", self.config._xtd_ai_config_error())
        self.icp.set_param(PARAM, KEY)
        self.assertFalse(self.config._xtd_ai_config_error())

    def test_provider_settings_from_params(self):
        s = self.settings(
            xtd_ai_agent_model="claude-sonnet-5-5",
            xtd_ai_agent_effort="high",
            xtd_ai_agent_timeout=12.0,
            xtd_ai_agent_workspace_id="wrkspc_9",
            xtd_ai_agent_log_error_details=True,
        )
        s.execute()
        cfg = self.config._xtd_ai_provider_settings()
        self.assertEqual(
            (
                cfg.model,
                cfg.effort,
                cfg.timeout,
                cfg.workspace_id,
                cfg.log_error_details,
            ),
            ("claude-sonnet-5-5", "high", 12.0, "wrkspc_9", True),
        )

    def test_workspace_falls_back_to_environment(self):
        with patch.dict("os.environ", {"ANTHROPIC_WORKSPACE_ID": "wrkspc_env"}):
            self.assertEqual(
                self.config._xtd_ai_provider_settings().workspace_id, "wrkspc_env"
            )
            self.icp.set_param("xtd_ai_agent.workspace_id", "wrkspc_ajustes")
            # Ajustes wins over the environment
            self.assertEqual(
                self.config._xtd_ai_provider_settings().workspace_id, "wrkspc_ajustes"
            )

    # -- prices ------------------------------------------------------------
    def test_prices_override_and_validation(self):
        self.icp.set_param(
            "xtd_ai_agent.prices_json", '{"x": {"input": 1, "output": 2}}'
        )
        prices = self.config._xtd_ai_prices()
        self.assertIn("x", prices)
        self.assertIn("claude-haiku-5-5", prices)
        self.icp.set_param("xtd_ai_agent.prices_json", "not json")
        self.assertIn("claude-haiku-5-5", self.config._xtd_ai_prices())
        with self.assertRaises(UserError):
            self.settings(xtd_ai_agent_prices_json="{broken").execute()

    # -- job runner --------------------------------------------------------
    def test_jobrunner_detection(self):
        with patch.dict(tools.config.options, {"server_wide_modules": ["base", "web"]}):
            self.assertFalse(self.config._xtd_ai_jobrunner_active())
            self.assertFalse(self.settings().xtd_ai_agent_jobrunner_active)
        with patch.dict(
            tools.config.options, {"server_wide_modules": ["base", "queue_job"]}
        ):
            self.assertTrue(self.config._xtd_ai_jobrunner_active())
            self.assertTrue(self.settings().xtd_ai_agent_jobrunner_active)

    # -- test connection ---------------------------------------------------
    def patch_http(self, items):
        http = HttpMock(items)
        patcher = patch.object(requests.Session, "post", http)
        patcher.start()
        self.addCleanup(patcher.stop)
        return http

    def test_connection_ok_sends_no_business_data(self):
        self.icp.set_param(PARAM, KEY)
        http = self.patch_http([message_json([{"type": "text", "text": "OK"}])])
        ok, message = self.config.with_user(self.admin)._xtd_ai_test_connection()
        self.assertTrue(ok, message)
        self.assertIn("Conexión correcta", message)
        body = http.bodies[0]
        self.assertNotIn("tools", body)
        self.assertEqual(body["max_tokens"], 16)
        self.assertEqual(len(body["messages"]), 1)
        self.assertEqual(
            body["messages"][0]["content"][0]["text"], "Prueba de conexión."
        )
        self.assertNotIn(KEY, message)

    def test_connection_error_message(self):
        self.icp.set_param(PARAM, KEY)
        self.patch_http([FakeResponse(401, {})])
        ok, message = self.config.with_user(self.admin)._xtd_ai_test_connection()
        self.assertFalse(ok)
        self.assertIn("401", message)
        self.assertNotIn(KEY, message)

    def test_connection_without_key(self):
        ok, message = self.config.with_user(self.admin)._xtd_ai_test_connection()
        self.assertFalse(ok)
        self.assertIn("Ajustes", message)

    def test_button_returns_notification(self):
        self.icp.set_param(PARAM, KEY)
        self.patch_http([message_json([{"type": "text", "text": "OK"}])])
        action = self.settings().action_xtd_ai_agent_test_connection()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "success")
