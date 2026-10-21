import json
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.bus.models.bus import BusBus

from ..tools.errors import XtdAiAuthError
from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestMcp(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, self.token = self.start_run()

    def test_initialize(self):
        status, response = self.rpc(
            self.user,
            self.run,
            "initialize",
            {"protocolVersion": "2025-06-18", "clientInfo": {"name": "t"}},
        )
        self.assertEqual(status, 200)
        result = response["result"]
        self.assertEqual(response["id"], 1)
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["serverInfo"]["name"], "xtd_ai_gateway")
        self.assertEqual(result["capabilities"], {"tools": {}})
        self.assertEqual(self.run.state, "running")
        self.assertTrue(self.run.started_at)

    def test_tools_list_shape_and_order(self):
        _status, response = self.rpc(self.user, self.run, "tools/list", {})
        tools = response["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertEqual(names, sorted(names))
        for expected in (
            "get_user_context",
            "load_skill",
            "search_partners",
            "get_partner_summary",
            "create_contact",
        ):
            self.assertIn(expected, names)
        self.assertEqual("search_products" in names, "product.product" in self.env)
        for tool in tools:
            schema = tool["inputSchema"]
            self.assertEqual(schema["type"], "object")
            self.assertIs(schema["additionalProperties"], False)
            self.assertIn("required", schema)
            self.assertEqual(
                set(tool["annotations"]),
                {"readOnlyHint", "destructiveHint", "xtdKind", "xtdSkill"},
            )
            self.assertIs(tool["annotations"]["destructiveHint"], False)
            self.assertEqual(
                tool["annotations"]["readOnlyHint"],
                tool["annotations"]["xtdKind"] == "read",
            )
        by_name = {t["name"]: t for t in tools}
        self.assertEqual(by_name["create_contact"]["annotations"]["xtdKind"], "create")
        self.assertIn(
            "contactos",
            by_name["load_skill"]["inputSchema"]["properties"]["skill"]["enum"],
        )

    def test_tools_list_filtered_by_groups(self):
        names = {
            t["name"]
            for t in self.rpc(self.user, self.run, "tools/list", {})[1]["result"][
                "tools"
            ]
        }
        self.assertNotIn("zz_test_manager_only", names)
        self.assertIn("create_contact", names)  # user has partner_manager
        run2, _t = self.start_run(self.user2)
        names2 = {
            t["name"]
            for t in self.rpc(self.user2, run2, "tools/list", {})[1]["result"]["tools"]
        }
        self.assertNotIn("create_contact", names2)
        run3, _t = self.start_run(self.manager)
        names3 = {
            t["name"]
            for t in self.rpc(self.manager, run3, "tools/list", {})[1]["result"][
                "tools"
            ]
        }
        self.assertIn("zz_test_manager_only", names3)

    def test_hidden_tool_is_not_callable(self):
        status, response = self.rpc(
            self.user,
            self.run,
            "tools/call",
            {"name": "zz_test_manager_only", "arguments": {}},
        )
        self.assertEqual((status, response["error"]["code"]), (200, -32601))

    def test_unknown_method_and_tool(self):
        status, response = self.rpc(self.user, self.run, "nope/nope", {})
        self.assertEqual((status, response["error"]["code"]), (200, -32601))
        status, response = self.rpc(
            self.user, self.run, "tools/call", {"name": "does_not_exist"}
        )
        self.assertEqual((status, response["error"]["code"]), (200, -32601))
        # unknown tool is audited too
        self.assertEqual(
            self.audits(self.run, event="tool_call", outcome="denied").mapped(
                "error_code"
            ),
            ["unknown_tool"],
        )

    def test_bad_params(self):
        for method, params in (
            ("tools/call", {}),
            ("tools/call", {"name": 5}),
            ("tools/call", {"name": "zz_test_echo", "arguments": []}),
            ("tools/list", []),
            ("xtd_ai/post_reply", {"status": "weird"}),
            ("xtd_ai/post_reply", {"text": 3, "status": "done"}),
            ("xtd_ai/post_reply", {"text": "x", "status": "done", "usage": 3}),
            ("initialize", {"protocolVersion": 3}),
        ):
            status, response = self.rpc(self.user, self.run, method, params)
            self.assertEqual(
                (status, response["error"]["code"]), (200, -32602), (method, params)
            )
        env = self.tool_env(self.user, self.run)
        for message in (
            [],
            "x",
            {"jsonrpc": "1.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "method": "initialize"},
            {"jsonrpc": "2.0", "id": 1, "method": 3},
        ):
            status, response = env["xtd.ai.mcp"]._xtd_ai_handle(message)
            self.assertEqual(
                (status, response["error"]["code"]), (200, -32600), message
            )

    def test_tool_call_ok(self):
        result = self.call(self.user, self.run, "zz_test_echo", {"text": "hi"})
        self.assertFalse(result["isError"])
        structured = result["structuredContent"]
        self.assertEqual(
            structured, {"status": "ok", "data": {"echo": "hi"}, "records": []}
        )
        self.assertEqual(json.loads(result["content"][0]["text"]), structured)
        self.assertEqual(result["content"][0]["type"], "text")

    def test_tool_call_schema_violation_is_validation_error(self):
        for args in ({}, {"text": 1}, {"text": "x" * 21}, {"text": "a", "extra": 1}):
            result = self.call(self.user, self.run, "zz_test_echo", args)
            self.assertTrue(result["isError"])
            self.assertEqual(result["structuredContent"]["error"]["code"], "validation")

    def test_tool_error_codes(self):
        expected = {
            "access": "access_denied",
            "user": "validation",
            "validation": "validation",
            "missing": "not_found",
            "not_found": "not_found",
            "ambiguous": "ambiguous",
            "internal": "internal",
            "draft": "draft_only",
        }
        for kind, code in expected.items():
            result = self.call(self.user, self.run, "zz_test_error", {"kind": kind})
            self.assertTrue(result["isError"], kind)
            structured = result["structuredContent"]
            self.assertEqual(structured["status"], "error")
            self.assertEqual(structured["error"]["code"], code, kind)
            if kind == "internal":
                self.assertNotIn("secret internal detail", result["content"][0]["text"])
            if kind == "ambiguous":
                self.assertEqual(structured["data"]["candidates"], [{"id": 1}])

    def test_tool_env(self):
        run = self.run
        result = self.call(self.user, run, "zz_test_env", cids=[self.company.id])
        data = result["structuredContent"]["data"]
        self.assertEqual(data["uid"], self.user.id)
        self.assertIs(data["su"], False)
        self.assertEqual(data["allowed_company_ids"], [self.company.id])
        self.assertEqual(data["xtd_ai_run"], run.id)

    def test_tool_call_counter_and_limit(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai_gateway.max_tool_calls_per_run", "3"
        )
        for _i in range(3):
            self.call(self.user, self.run, "zz_test_echo", {"text": "a"})
        self.assertEqual(self.run.tool_calls, 3)
        status, response = self.rpc(
            self.user,
            self.run,
            "tools/call",
            {"name": "zz_test_echo", "arguments": {"text": "a"}},
        )
        self.assertEqual((status, response["error"]["code"]), (409, -32004))

    def test_history(self):
        conversation = self.run.conversation_id
        self.env["xtd.ai.message"].sudo().create(
            {"conversation_id": conversation.id, "role": "assistant", "body": "bye"}
        )
        self.env["xtd.ai.message"].sudo().create(
            {"conversation_id": conversation.id, "role": "notice", "body": "notice"}
        )
        _status, response = self.rpc(self.user, self.run, "xtd_ai/history", {})
        history = response["result"]
        self.assertEqual(
            set(history),
            {
                "user",
                "company",
                "allowed_companies",
                "today",
                "confirm_writes",
                "messages",
            },
        )
        self.assertEqual(history["user"]["name"], self.user.name)
        self.assertEqual(history["company"]["id"], self.company.id)
        self.assertEqual(history["company"]["currency"], self.company.currency_id.name)
        self.assertEqual(
            history["allowed_companies"],
            [{"id": self.company.id, "name": self.company.name}],
        )
        self.assertTrue(history["confirm_writes"])
        self.assertRegex(history["today"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(
            [(m["role"], m["text"]) for m in history["messages"]],
            [("user", "hola"), ("assistant", "bye")],
        )
        self.assertIn("date", history["messages"][0])

    def test_history_tools_used(self):
        self.call(self.user, self.run, "zz_test_echo", {"text": "secret-arg"})
        self.rpc(
            self.user, self.run, "xtd_ai/post_reply", {"text": "ok", "status": "done"}
        )
        run, _token = self.start_run(self.user)
        messages = self.rpc(self.user, run, "xtd_ai/history", {})[1]["result"][
            "messages"
        ]
        assistant = [m for m in messages if m["role"] == "assistant"][-1]
        self.assertEqual(
            [(t["tool"], t["outcome"]) for t in assistant["tools_used"]],
            [("zz_test_echo", "ok")],
        )
        self.assertNotIn("secret-arg", str(assistant["tools_used"]))
        self.assertNotIn("tools_used", [m for m in messages if m["role"] == "user"][0])

    def test_history_limited_to_20(self):
        conversation = self.run.conversation_id
        for index in range(30):
            self.env["xtd.ai.message"].sudo().create(
                {
                    "conversation_id": conversation.id,
                    "role": "assistant",
                    "body": f"m{index}",
                }
            )
        messages = self.rpc(self.user, self.run, "xtd_ai/history", {})[1]["result"][
            "messages"
        ]
        self.assertEqual(len(messages), 20)
        self.assertEqual(messages[-1]["text"], "m29")

    def test_post_reply_closes_run_and_notifies(self):
        usage = {
            "provider": "fake",
            "model": "m",
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_tokens": 1,
            "cache_write_tokens": 2,
            "iterations": 3,
            "tool_calls": 99,
            "cost_estimate": 0.25,
        }
        self.call(self.user, self.run, "zz_test_echo", {"text": "a"})
        with patch.object(BusBus, "_sendone") as sendone:
            status, response = self.rpc(
                self.user,
                self.run,
                "xtd_ai/post_reply",
                {"text": "Listo", "status": "done", "usage": usage},
            )
        self.assertEqual(status, 200)
        message = (
            self.env["xtd.ai.message"].sudo().browse(response["result"]["message_id"])
        )
        self.assertEqual(
            (message.role, message.body, message.run_id),
            ("assistant", "Listo", self.run),
        )
        run = self.run
        self.assertEqual(run.state, "done")
        self.assertTrue(run.finished_at)
        self.assertEqual((run.input_tokens, run.output_tokens), (10, 5))
        self.assertEqual((run.cache_read_tokens, run.cache_write_tokens), (1, 2))
        self.assertEqual((run.provider, run.model, run.iterations), ("fake", "m", 3))
        self.assertEqual(run.cost_estimate, 0.25)
        self.assertEqual(
            run.tool_calls, 1
        )  # counted by the gateway, not by the service
        sendone.assert_called_once()
        target, notification_type, payload = sendone.call_args.args
        self.assertEqual(target, self.user.partner_id)
        self.assertEqual(notification_type, "xtd_ai/update")
        self.assertEqual(
            payload,
            {
                "conversation_id": run.conversation_id.id,
                "message_id": message.id,
                "run_id": run.id,
                "state": "done",
            },
        )
        # the run is over: the token no longer works
        with self.assertRaises(XtdAiAuthError):
            self.authenticate(self.token)

    def test_post_reply_failed(self):
        status, response = self.rpc(
            self.user,
            self.run,
            "xtd_ai/post_reply",
            {"text": "", "status": "failed", "error": "boom"},
        )
        self.assertEqual(status, 200)
        message = (
            self.env["xtd.ai.message"].sudo().browse(response["result"]["message_id"])
        )
        self.assertEqual((message.role, message.body), ("notice", "boom"))
        self.assertEqual((self.run.state, self.run.error), ("failed", "boom"))

    def test_post_reply_links_pending_actions_and_records(self):
        self.call(self.user, self.run, "zz_test_create", {"name": "tag-link"})
        _status, response = self.rpc(
            self.user, self.run, "xtd_ai/post_reply", {"text": "ok", "status": "done"}
        )
        message = (
            self.env["xtd.ai.message"].sudo().browse(response["result"]["message_id"])
        )
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .search([("run_id", "=", self.run.id)])
        )
        self.assertEqual(message.pending_action_ids, action)
        history = self.start_after_done()
        self.assertIn(f"[Acción #{action.id}: pendiente de confirmación]", history)

    def start_after_done(self):
        run, _token = self.start_run(self.user)
        messages = self.rpc(self.user, run, "xtd_ai/history", {})[1]["result"][
            "messages"
        ]
        return "\n".join(m["text"] for m in messages)

    def test_post_reply_cancelled_run_is_rejected_by_auth(self):
        self.run.state = "cancelled"
        with self.assertRaises(XtdAiAuthError):
            self.authenticate(self.token)

    def test_cancel_run_by_owner_only(self):
        with self.assertRaises(AccessError):
            self.run.with_user(self.user2).action_cancel()
        self.run.with_user(self.user).action_cancel()
        self.assertEqual(self.run.state, "cancelled")
        with self.assertRaises(XtdAiAuthError):
            self.authenticate(self.token)

    def test_tool_methods_are_not_rpc_callable(self):
        from odoo.service.model import get_public_method

        toolbox = self.env["xtd.ai.toolbox.common"]
        for tool in toolbox._xtd_ai_tools().values():
            if tool["model"] != "xtd.ai.toolbox.common":
                continue
            with self.assertRaises(AccessError, msg=tool["name"]):
                get_public_method(toolbox, tool["attr"])
        for model, method in (
            ("xtd.ai.mcp", "_xtd_ai_handle"),
            ("xtd.ai.token", "_xtd_ai_mint"),
        ):
            with self.assertRaises(AccessError):
                get_public_method(self.env[model], method)
