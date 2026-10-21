import base64
import io
import json
import os
from unittest.mock import patch

from odoo.tests import TransactionCase
from odoo.tests.common import new_test_user
from odoo.tools.pdf import PdfWriter

SERVICE_KEY = "test-service-key-0123456789abcdef0123456789abcdef"
AI_GROUPS = "base.group_user,xtd_ai_gateway.group_xtd_ai_user"


def make_pdf(pages=1):
    """A small valid PDF with ``pages`` blank pages."""
    writer = PdfWriter()
    for _i in range(pages):
        writer.add_blank_page(width=200, height=200)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def make_png():
    """A tiny valid PNG (1x1 pixel)."""
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
        "hKmMIQAAAABJRU5ErkJggg=="
    )


class XtdAiCase(TransactionCase):
    """Base class: users, runs and a helper to speak to the MCP handler."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env_patch = patch.dict(os.environ, {"XTD_AI_SERVICE_KEY": SERVICE_KEY})
        cls.env_patch.start()
        cls.addClassCleanup(cls.env_patch.stop)
        cls.company = cls.env.company
        company_vals = {"name": "AI other company"}
        if "fiscalyear_last_day" in cls.env["res.company"]._fields:  # account installed
            company_vals.update(fiscalyear_last_day=31, fiscalyear_last_month="12")
        cls.company2 = cls.env["res.company"].create(company_vals)
        cls.user = new_test_user(
            cls.env, "xtd_ai_u1", groups=AI_GROUPS + ",base.group_partner_manager"
        )
        cls.user2 = new_test_user(cls.env, "xtd_ai_u2", groups=AI_GROUPS)
        cls.manager = new_test_user(
            cls.env, "xtd_ai_mgr", groups="xtd_ai_gateway.group_xtd_ai_manager"
        )
        cls.plain = new_test_user(cls.env, "xtd_ai_plain", groups="base.group_user")
        cls.portal = new_test_user(cls.env, "xtd_ai_portal", groups="base.group_portal")

    # -- runs ------------------------------------------------------------
    def start_run(self, user=None, text="hola", attachment_ids=None):
        user = user or self.user
        run, token = (
            self.env["xtd.ai.conversation"]
            .with_user(user)
            ._xtd_ai_start_run(text, attachment_ids=attachment_ids)
        )
        return run.sudo(), token

    def upload(self, user=None, raw=None, name="factura.pdf", conversation=None):
        """Create a chat attachment as ``user`` in their open conversation."""
        user = user or self.user
        conversation = (
            conversation
            or self.env["xtd.ai.conversation"].with_user(user)._xtd_ai_open()
        )
        return (
            self.env["ir.attachment"]
            .with_user(user)
            .create(
                {
                    "name": name,
                    "raw": raw if raw is not None else make_pdf(),
                    "res_model": "xtd.ai.conversation",
                    "res_id": conversation.id,
                }
            )
        )

    def headers(self, token, key=SERVICE_KEY):
        headers = {"Authorization": f"Bearer {token}"}
        if key is not None:
            headers["X-XTD-AI-Service-Key"] = key
        return headers

    def authenticate(self, token, key=SERVICE_KEY, dbname=None):
        env_su = self.env(user=1, su=True)
        return env_su["xtd.ai.token"]._xtd_ai_authenticate(
            self.headers(token, key), dbname or self.env.cr.dbname
        )

    def tool_env(self, user, run, cids=None):
        """The environment the auth method builds for a request."""
        return self.env(
            user=user.id,
            su=False,
            context={
                "allowed_company_ids": cids or [self.company.id],
                "lang": user.lang or "en_US",
                "tz": user.tz or "UTC",
                "xtd_ai_run": run.id,
                "mail_auto_subscribe_no_notify": True,
                "mail_notify_force_send": False,
            },
        )

    def rpc(self, user, run, method, params=None, cids=None, rid=1):
        env = self.tool_env(user, run, cids)
        message = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            message["params"] = params
        return env["xtd.ai.mcp"]._xtd_ai_handle(message)

    def call(self, user, run, name, arguments=None, **kw):
        """tools/call; returns the ToolResult (asserts HTTP 200 and no RPC error)."""
        status, response = self.rpc(
            user, run, "tools/call", {"name": name, "arguments": arguments or {}}, **kw
        )
        self.assertEqual(status, 200, response)
        self.assertIn("result", response, response)
        return response["result"]

    def set_confirm(self, user, value):
        user.sudo().xtd_ai_confirm_writes = value

    def audits(self, run, **domain):
        dom = [("run_id", "=", run.id)] + [(k, "=", v) for k, v in domain.items()]
        return self.env["xtd.ai.audit"].sudo().search(dom, order="id")


def body(response):
    return json.loads(response.text)
