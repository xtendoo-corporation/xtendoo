import json
import os
from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

from .common import AI_GROUPS, SERVICE_KEY


@tagged("post_install", "-at_install")
class TestXtdAiHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, "xtd_ai_http", groups=AI_GROUPS)
        cls.env_patch = patch.dict(os.environ, {"XTD_AI_SERVICE_KEY": SERVICE_KEY})
        cls.env_patch.start()
        cls.addClassCleanup(cls.env_patch.stop)

    def start_run(self):
        run, token = (
            self.env["xtd.ai.conversation"]
            .with_user(self.user)
            ._xtd_ai_start_run("hola")
        )
        return run, token

    def mcp(self, token, message=None, key=SERVICE_KEY, extra=None, raw=None):
        headers = {
            "X-Odoo-Database": self.env.cr.dbname,
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if key is not None:
            headers["X-XTD-AI-Service-Key"] = key
        headers.update(extra or {})
        data = (
            raw
            if raw is not None
            else json.dumps(
                message
                or {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            )
        )
        return self.url_open("/xtd_ai/mcp", data=data, headers=headers)

    def test_initialize_ok_and_json_error_bodies(self):
        _run, token = self.start_run()
        response = self.mcp(token)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(body["result"]["serverInfo"]["name"], "xtd_ai_gateway")

    def test_auth_failures(self):
        run, token = self.start_run()
        for kwargs, status, code in (
            ({"token": None}, 401, -32001),
            ({"token": "xtdai1.a.b"}, 401, -32001),
            ({"token": token, "key": None}, 401, -32001),
            ({"token": token, "key": "bad"}, 401, -32001),
        ):
            response = self.mcp(**kwargs)
            self.assertEqual(response.status_code, status, kwargs)
            self.assertEqual(response.json()["error"]["code"], code)
        with patch.dict(os.environ):
            os.environ.pop("XTD_AI_SERVICE_KEY")
            response = self.mcp(token)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], -32010)
        # failures are audited without the token
        audits = self.env["xtd.ai.audit"].sudo().search([("event", "=", "auth_failed")])
        self.assertTrue(audits)
        for audit in audits:
            self.assertNotIn(token, json.dumps([audit.error_code, audit.arguments]))
        # a finished run is a 409
        run.sudo().state = "cancelled"
        response = self.mcp(token)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], -32004)

    def test_session_cookie_is_not_accepted(self):
        self.authenticate("xtd_ai_http", "xtd_ai_httpxxxx")
        response = self.url_open(
            "/xtd_ai/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
            headers={
                "Content-Type": "application/json",
                "X-XTD-AI-Service-Key": SERVICE_KEY,
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_token_is_not_an_api_key(self):
        _run, token = self.start_run()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Odoo-Database": self.env.cr.dbname,
            "Content-Type": "application/json",
            "X-XTD-AI-Service-Key": SERVICE_KEY,
        }
        response = self.url_open(
            "/json/2/res.partner/search_read",
            data=json.dumps({"fields": ["name"]}),
            headers=headers,
        )
        self.assertIn(response.status_code, (401, 403), response.text)
        self.assertNotIn('"result"', response.text)
        response = self.url_open(
            "/jsonrpc",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "id": 1,
                    "params": {
                        "service": "object",
                        "method": "execute_kw",
                        "args": [
                            self.env.cr.dbname,
                            self.user.id,
                            token,
                            "res.partner",
                            "search_read",
                            [[]],
                            {"fields": ["name"]},
                        ],
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertNotIn('"result"', response.text)
        response = self.url_open(
            "/web/session/get_session_info",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": {}}),
            headers=headers,
        )
        self.assertNotIn(str(self.user.login), response.text)

    def test_mcp_requires_post_and_valid_json(self):
        _run, token = self.start_run()
        response = self.url_open(
            "/xtd_ai/mcp",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Odoo-Database": self.env.cr.dbname,
                "X-XTD-AI-Service-Key": SERVICE_KEY,
            },
        )
        self.assertNotEqual(response.status_code, 200)
        response = self.mcp(token, raw="{not json")
        self.assertEqual(response.json()["error"]["code"], -32700)

    def test_tools_call_over_http(self):
        run, token = self.start_run()
        response = self.mcp(
            token,
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "get_user_context", "arguments": {}},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(
            result["structuredContent"]["data"]["user"]["id"], self.user.id
        )
        self.assertEqual(run.state, "running")
