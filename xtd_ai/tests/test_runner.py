import json

from odoo.tests import tagged

from ..tools.errors import XtdAiAuthError, XtdAiRpcError
from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestRunnerEnv(XtdAiCase):
    """In-process dispatch and runner environment (CONTRACT section 15)."""

    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run()

    def runner_env(self, run=None):
        return self.env["xtd.ai.run"]._xtd_ai_runner_env(run or self.run)

    def test_cids_stored_at_start(self):
        self.assertEqual(self.run.cids, [self.user.company_id.id])
        user = self.user
        user.company_ids = [(4, self.company2.id)]
        conversation = self.env["xtd.ai.conversation"].with_user(user)._xtd_ai_open()
        conversation.sudo().run_ids.write({"state": "done"})
        run, _t = conversation.with_context(
            allowed_company_ids=[self.company2.id, self.company.id]
        )._xtd_ai_start_run("otra")
        self.assertEqual(run.sudo().cids, [self.company2.id, self.company.id])
        self.assertEqual(run.sudo().company_id, self.company2)

    def test_runner_env_shape(self):
        env = self.runner_env()
        self.assertEqual(env.uid, self.user.id)
        self.assertFalse(env.su)
        ctx = env.context
        self.assertEqual(ctx["allowed_company_ids"], self.run.cids)
        self.assertEqual(ctx["xtd_ai_run"], self.run.id)
        self.assertEqual(ctx["lang"], self.user.lang or "en_US")
        self.assertEqual(ctx["tz"], self.user.tz or "UTC")
        self.assertTrue(ctx["mail_auto_subscribe_no_notify"])
        self.assertIs(ctx["mail_notify_force_send"], False)
        # equal to the environment of the HTTP auth method
        self.assertEqual(
            dict(env.context), dict(self.tool_env(self.user, self.run).context)
        )

    def assertRevalidationFails(self, status, code, reason=None):
        with self.assertRaises(XtdAiAuthError) as cm:
            self.runner_env()
        self.assertEqual(
            (cm.exception.http_status, cm.exception.rpc_code), (status, code)
        )
        if reason:
            self.assertEqual(cm.exception.reason, reason)

    def test_revalidate_inactive_user(self):
        self.user.active = False
        self.assertRevalidationFails(401, -32001, "user_not_allowed")

    def test_revalidate_group_removed(self):
        self.user.write(
            {"group_ids": [(3, self.env.ref("xtd_ai.group_xtd_ai_user").id)]}
        )
        self.assertRevalidationFails(401, -32001, "user_not_allowed")

    def test_revalidate_conversation_closed(self):
        self.run.conversation_id.state = "closed"
        self.assertRevalidationFails(401, -32001, "conversation_closed")

    def test_revalidate_run_cancelled_or_done(self):
        self.run._xtd_ai_finish("cancelled")
        self.assertRevalidationFails(409, -32004, "run_not_active")
        self.run.state = "done"
        self.assertRevalidationFails(409, -32004)

    def test_revalidate_company_removed(self):
        self.user.company_ids = [(4, self.company2.id)]
        self.run.cids = [self.company2.id]
        self.runner_env()  # still allowed
        self.user.company_ids = [(3, self.company2.id)]
        self.assertRevalidationFails(403, -32003, "company_not_allowed")

    def test_dispatch_equals_http_handler(self):
        env = self.runner_env()
        mcp = env["xtd.ai.mcp"]
        for method, params in (
            ("initialize", {"protocolVersion": "2025-06-18"}),
            ("tools/list", {}),
            ("xtd_ai/history", {}),
            ("tools/call", {"name": "get_user_context", "arguments": {}}),
        ):
            _status, response = self.rpc(self.user, self.run, method, params)
            result = mcp._xtd_ai_dispatch(method, params)
            self.assertEqual(
                json.dumps(result, sort_keys=True, default=str),
                json.dumps(response["result"], sort_keys=True, default=str),
                method,
            )

    def test_dispatch_audit_and_count(self):
        env = self.runner_env()
        result = env["xtd.ai.mcp"]._xtd_ai_dispatch(
            "tools/call", {"name": "get_user_context", "arguments": {}}
        )
        self.assertFalse(result["isError"])
        audit = self.audits(self.run, tool_name="get_user_context")
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.outcome, "ok")
        self.assertEqual(self.run.tool_calls, 1)

    def test_dispatch_raises_rpc_errors(self):
        env = self.runner_env()
        mcp = env["xtd.ai.mcp"]
        with self.assertRaises(XtdAiRpcError) as cm:
            mcp._xtd_ai_dispatch("nope", {})
        self.assertEqual(cm.exception.rpc_code, -32601)
        with self.assertRaises(XtdAiRpcError) as cm:
            mcp._xtd_ai_dispatch("tools/call", {"name": 5})
        self.assertEqual(cm.exception.rpc_code, -32602)

    def test_dispatch_post_reply(self):
        env = self.runner_env()
        result = env["xtd.ai.mcp"]._xtd_ai_dispatch(
            "xtd_ai/post_reply", {"text": "hola", "status": "done", "usage": {}}
        )
        self.assertTrue(result["message_id"])
        self.assertEqual(self.run.state, "done")
