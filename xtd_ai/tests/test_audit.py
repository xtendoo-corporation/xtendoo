import contextlib
import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestAudit(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, self.token = self.start_run()

    def own_cursor(self):
        """auth_failed rows use their own cursor; reuse the test one so nothing is
        committed."""
        return patch.object(
            type(self.env.registry),
            "cursor",
            lambda reg: contextlib.nullcontext(self.env.cr),
        )

    def test_one_row_per_call(self):
        self.set_confirm(self.user, True)
        self.call(self.user, self.run, "zz_test_echo", {"text": "a"})
        self.call(self.user, self.run, "zz_test_error", {"kind": "user"})
        self.call(self.user, self.run, "zz_test_error", {"kind": "access"})
        self.call(self.user, self.run, "zz_test_draft", {"name": "t"})
        self.call(self.user, self.run, "zz_test_echo", {})  # schema violation
        self.rpc(
            self.user, self.run, "tools/call", {"name": "unknown", "arguments": {}}
        )
        rows = self.audits(self.run)
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            rows.mapped("tool_name"),
            [
                "zz_test_echo",
                "zz_test_error",
                "zz_test_error",
                "zz_test_draft",
                "zz_test_echo",
                "unknown",
            ],
        )
        self.assertEqual(
            rows.mapped("outcome"),
            ["ok", "error", "denied", "pending", "error", "denied"],
        )
        self.assertEqual(
            rows.mapped("error_code"),
            [False, "validation", "access_denied", False, "validation", "unknown_tool"],
        )
        for row in rows:
            self.assertEqual(row.user_id, self.user)
            self.assertEqual(row.company_id, self.company)
            self.assertGreaterEqual(row.duration_ms, 0)
        self.assertEqual(rows[0].arguments, {"text": "a"})

    def test_records_and_long_texts(self):
        result = self.call(self.user, self.run, "zz_test_env")
        row = self.audits(self.run)[-1]
        self.assertEqual(row.record_refs[0]["model"], "res.users")
        self.assertEqual(result["structuredContent"]["records"][0]["id"], self.user.id)
        self.env["xtd.ai.audit"]._xtd_ai_log(
            "tool_call",
            "ok",
            run_id=self.run.id,
            arguments={"a": "x" * 1000, "n": ["y" * 500, 3]},
        )
        row = self.audits(self.run)[-1]
        self.assertEqual(len(row.arguments["a"]), 303)
        self.assertEqual(len(row.arguments["n"][0]), 303)
        self.assertEqual(row.arguments["n"][1], 3)

    def test_token_never_stored(self):
        self.call(self.user, self.run, "zz_test_echo", {"text": "a"})
        self.rpc(
            self.user, self.run, "tools/call", {"name": "zz_test_echo", "arguments": []}
        )
        with contextlib.suppress(Exception):
            self.authenticate(self.token + "tampered")
        with self.own_cursor():
            self.env["xtd.ai.audit"]._xtd_ai_log_auth_failed(
                self.env.registry, "bad_signature"
            )
        for row in self.env["xtd.ai.audit"].sudo().search([]):
            dump = json.dumps(row.read()[0], default=str)
            self.assertNotIn("xtdai1", dump)
            self.assertNotIn(self.token.split(".")[2], dump)
        run_dump = json.dumps(self.run.read()[0], default=str)
        self.assertNotIn(self.token.split(".")[1], run_dump)

    def test_auth_failed_event(self):
        with self.own_cursor():
            self.env["xtd.ai.audit"]._xtd_ai_log_auth_failed(
                self.env.registry, "bad_signature", self.user.id, self.run.id
            )
        row = self.audits(self.run, event="auth_failed")
        self.assertEqual(
            (row.outcome, row.error_code, row.user_id),
            ("denied", "bad_signature", self.user),
        )

    def test_access_rights(self):
        self.call(self.user, self.run, "zz_test_echo", {"text": "a"})
        audit_model = self.env["xtd.ai.audit"]
        for user in (self.user, self.user2, self.plain):
            with self.assertRaises(AccessError, msg=user.login):
                audit_model.with_user(user).search([])
        rows = audit_model.with_user(self.manager).search(
            [("run_id", "=", self.run.id)]
        )
        self.assertEqual(len(rows), 1)
        # nobody writes or deletes through the ORM without sudo
        for user in (self.manager, self.user):
            with self.assertRaises(AccessError):
                audit_model.with_user(user).create(
                    {"event": "tool_call", "outcome": "ok"}
                )
        with self.assertRaises(AccessError):
            rows.with_user(self.manager).write({"outcome": "error"})
        with self.assertRaises(AccessError):
            rows.with_user(self.manager).unlink()
        # not even with sudo (immutability), except the retention purge
        with self.assertRaises(AccessError):
            rows.sudo().write({"outcome": "error"})
        with self.assertRaises(AccessError):
            rows.sudo().unlink()
        self.assertTrue(rows.exists())

    def test_retention_cron(self):
        old = self.env["xtd.ai.audit"]._xtd_ai_log(
            "tool_call", "ok", tool_name="old_one"
        )
        fresh = self.env["xtd.ai.audit"]._xtd_ai_log(
            "tool_call", "ok", tool_name="fresh_one"
        )
        self.env.cr.execute(
            "UPDATE xtd_ai_audit SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=400), old.id),
        )
        self.env["xtd.ai.audit"].invalidate_model()
        self.env["xtd.ai.audit"]._xtd_ai_cron_purge()
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.audit_retention_days", "1"
        )
        self.env.cr.execute(
            "UPDATE xtd_ai_audit SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=3), fresh.id),
        )
        self.env["xtd.ai.audit"].invalidate_model()
        self.env["xtd.ai.audit"]._xtd_ai_cron_purge()
        self.assertFalse(fresh.exists())

    def test_conversation_message_run_rules(self):
        run2, _t = self.start_run(self.user2)
        convs = self.env["xtd.ai.conversation"]
        self.assertEqual(
            convs.with_user(self.user).search([]), self.run.conversation_id
        )
        self.assertEqual(convs.with_user(self.user2).search([]), run2.conversation_id)
        self.assertEqual(
            convs.with_user(self.manager).search(
                [("id", "in", (self.run.conversation_id | run2.conversation_id).ids)]
            ),
            self.run.conversation_id | run2.conversation_id,
        )
        with self.assertRaises(AccessError):
            self.run.conversation_id.with_user(self.manager).write({"name": "hack"})
        self.assertEqual(
            self.env["xtd.ai.message"]
            .with_user(self.user)
            .search([])
            .mapped("conversation_id"),
            self.run.conversation_id,
        )
        runs = self.env["xtd.ai.run"].with_user(self.user).search([])
        self.assertEqual(runs, self.run)
        with self.assertRaises(AccessError):
            runs.write({"state": "done"})
        with self.assertRaises(AccessError):
            self.env["xtd.ai.message"].with_user(self.user).create(
                {
                    "conversation_id": self.run.conversation_id.id,
                    "role": "assistant",
                    "body": "forged",
                }
            )
        with self.assertRaises(AccessError):
            convs.with_user(self.plain).search([])
        # the jti is not readable by regular users
        with self.assertRaises(AccessError):
            runs.mapped("jti")

    def test_user_preference(self):
        self.assertTrue(self.user.xtd_ai_confirm_writes)
        self.user.with_user(self.user).write({"xtd_ai_confirm_writes": False})
        self.assertFalse(self.user.xtd_ai_confirm_writes)
