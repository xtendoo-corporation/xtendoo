from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestWriteFlow(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run()
        self.tags = self.env["res.partner.category"]

    def tag_count(self, name):
        return self.tags.sudo().search_count([("name", "=", name)])

    def propose(self, tool="zz_test_draft", name="tag-a", user=None, run=None):
        result = self.call(user or self.user, run or self.run, tool, {"name": name})
        return result["structuredContent"]

    def test_confirmation_on_creates_pending_and_writes_nothing(self):
        self.set_confirm(self.user, True)
        structured = self.propose()
        self.assertEqual(structured["status"], "pending_confirmation")
        self.assertIn("tag-a", structured["summary"])
        self.assertEqual(self.tag_count("tag-a"), 0)
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(structured["pending_action_id"])
        )
        self.assertEqual(
            (action.state, action.tool_name, action.user_id),
            ("pending", "zz_test_draft", self.user),
        )
        self.assertEqual(action.arguments, {"name": "tag-a"})
        self.assertEqual(action.preview["summary"], structured["summary"])
        self.assertEqual(action.run_id, self.run)
        self.assertAlmostEqual(
            (action.expires_at - fields.Datetime.now()).total_seconds(),
            24 * 3600,
            delta=120,
        )
        audit = self.audits(self.run, event="tool_call")
        self.assertEqual(audit.mapped("outcome"), ["pending"])

    def test_confirmation_off_executes_directly(self):
        self.set_confirm(self.user, False)
        structured = self.propose(name="tag-direct")
        self.assertEqual(structured["status"], "ok")
        self.assertEqual(structured["records"][0]["model"], "res.partner.category")
        self.assertEqual(self.tag_count("tag-direct"), 1)
        self.assertFalse(
            self.env["xtd.ai.pending_action"]
            .sudo()
            .search([("run_id", "=", self.run.id)])
        )

    def test_create_kind_always_needs_confirmation(self):
        self.set_confirm(self.user, False)
        structured = self.propose("zz_test_create", "tag-create")
        self.assertEqual(structured["status"], "pending_confirmation")
        self.assertEqual(self.tag_count("tag-create"), 0)

    def test_force_confirmation_param(self):
        self.set_confirm(self.user, False)
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.force_confirmation", "True"
        )
        self.assertEqual(
            self.propose(name="tag-forced")["status"], "pending_confirmation"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.force_confirmation", "False"
        )
        self.assertEqual(self.propose(name="tag-unforced")["status"], "ok")

    def test_confirm_executes_as_session_user(self):
        pending = self.propose(name="tag-confirmed")
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.user)
            .browse(pending["pending_action_id"])
        )
        result = action.action_confirm()
        self.assertEqual(result["state"], "confirmed")
        self.assertIsNone(result["error"])
        tag = self.tags.sudo().search([("name", "=", "tag-confirmed")])
        self.assertEqual(len(tag), 1)
        self.assertEqual(tag.create_uid, self.user)
        action = action.sudo()
        self.assertEqual(
            (action.state, action.result_model, action.result_res_id),
            ("confirmed", "res.partner.category", tag.id),
        )
        self.assertEqual(
            self.audits(self.run, event="confirm").mapped("outcome"), ["ok"]
        )
        # cannot be confirmed twice
        with self.assertRaises(UserError):
            action.with_user(self.user).action_confirm()
        self.assertEqual(self.tag_count("tag-confirmed"), 1)

    def test_confirm_runs_with_run_context_and_guards(self):
        # the confirmed execution is still under xtd_ai_run: the guard blocks the
        # chatter
        pending = self.propose(name="tag-ctx")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(pending["pending_action_id"])
        )
        action.arguments = {"name": "tag-ctx"}
        result = action.with_user(self.user).action_confirm()
        self.assertEqual(result["state"], "confirmed")

    def test_confirm_failure_marks_failed_and_rolls_back(self):
        # user2 lacks partner_manager: creating a tag is an AccessError
        run2, _t = self.start_run(self.user2)
        self.set_confirm(self.user2, True)
        pending = self.propose("zz_test_draft", "tag-denied", user=self.user2, run=run2)
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.user2)
            .browse(pending["pending_action_id"])
        )
        result = action.action_confirm()
        self.assertEqual(result["state"], "failed")
        self.assertTrue(result["error"])
        self.assertEqual(self.tag_count("tag-denied"), 0)
        self.assertEqual(action.sudo().state, "failed")
        self.assertEqual(
            self.audits(run2, event="confirm").mapped("outcome"), ["denied"]
        )

    def test_cancel(self):
        pending = self.propose(name="tag-cancel")
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.user)
            .browse(pending["pending_action_id"])
        )
        self.assertEqual(action.action_cancel(), {"state": "cancelled"})
        self.assertEqual(action.sudo().state, "cancelled")
        self.assertEqual(self.tag_count("tag-cancel"), 0)
        self.assertEqual(
            self.audits(self.run, event="cancel").mapped("outcome"), ["ok"]
        )
        with self.assertRaises(UserError):
            action.action_confirm()
        with self.assertRaises(UserError):
            action.action_cancel()

    def test_expired_action_cannot_be_confirmed(self):
        pending = self.propose(name="tag-expired")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(pending["pending_action_id"])
        )
        action.expires_at = fields.Datetime.now() - timedelta(minutes=1)
        with self.assertRaises(UserError):
            action.with_user(self.user).action_confirm()
        self.assertEqual(self.tag_count("tag-expired"), 0)
        self.env["xtd.ai.run"]._xtd_ai_cron_housekeeping()
        self.assertEqual(action.state, "expired")
        with self.assertRaises(UserError):
            action.with_user(self.user).action_confirm()

    def test_other_user_cannot_confirm_or_cancel(self):
        pending = self.propose(name="tag-other")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(pending["pending_action_id"])
        )
        for other in (self.user2, self.manager):
            with self.assertRaises(AccessError):
                action.with_user(other).action_confirm()
            with self.assertRaises(AccessError):
                action.with_user(other).action_cancel()
            self.assertFalse(
                self.env["xtd.ai.pending_action"]
                .with_user(other)
                .search([("id", "=", action.id)])
            )
        self.assertEqual(action.state, "pending")
        self.assertEqual(self.tag_count("tag-other"), 0)

    def test_confirm_not_possible_from_agent_context_or_superuser(self):
        pending = self.propose(name="tag-self")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(pending["pending_action_id"])
        )
        with self.assertRaises(AccessError):  # superuser mode
            action.action_confirm()
        agent_env = self.tool_env(self.user, self.run)
        with self.assertRaises(
            AccessError
        ):  # inside an AI run (token-authenticated request)
            agent_env["xtd.ai.pending_action"].browse(action.id).action_confirm()
        with self.assertRaises(AccessError):
            agent_env["xtd.ai.pending_action"].browse(action.id).action_cancel()
        self.assertEqual(action.state, "pending")

    def test_confirm_revalidates_arguments(self):
        pending = self.propose(name="tag-valid")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(pending["pending_action_id"])
        )
        action.arguments = {"name": "x" * 80, "extra": True}  # tampered row
        result = action.with_user(self.user).action_confirm()
        self.assertEqual(result["state"], "failed")
        self.assertEqual(self.tag_count("x" * 80), 0)

    def test_confirm_rejects_foreign_companies(self):
        pending = self.propose(name="tag-cids")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(pending["pending_action_id"])
        )
        action.cids = [self.company2.id]
        result = action.with_user(self.user).action_confirm()
        self.assertEqual(result["state"], "failed")

    def test_users_cannot_create_or_edit_actions_via_orm(self):
        pending = self.propose(name="tag-orm")
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.user)
            .browse(pending["pending_action_id"])
        )
        with self.assertRaises(AccessError):
            action.write({"state": "confirmed"})
        with self.assertRaises(AccessError):
            self.env["xtd.ai.pending_action"].with_user(self.user).create(
                {
                    "run_id": self.run.id,
                    "conversation_id": self.run.conversation_id.id,
                    "user_id": self.user.id,
                    "tool_name": "x",
                }
            )

    def test_history_shows_final_state(self):
        pending = self.propose(name="tag-hist")
        self.rpc(
            self.user,
            self.run,
            "xtd_ai/post_reply",
            {"text": "preparado", "status": "done"},
        )
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.user)
            .browse(pending["pending_action_id"])
        )
        action.action_confirm()
        run2, _t = self.start_run(self.user, "otra")
        messages = self.rpc(self.user, run2, "xtd_ai/history", {})[1]["result"][
            "messages"
        ]
        text = next(m["text"] for m in messages if m["role"] == "assistant")
        self.assertIn(f"[Acción #{action.id}: creada tag-hist]", text)
        action2 = self.env["xtd.ai.pending_action"].sudo().browse(action.id)
        self.assertEqual(action2.state, "confirmed")

    def test_preview_cannot_write(self):
        # zz_test_draft preview is harmless; here we verify the savepoint wrapper by
        # patching a preview that creates a record: it must be rolled back.
        toolbox = self.tool_env(self.user, self.run)["xtd.ai.toolbox.test"]
        tool = toolbox._xtd_ai_tools()["zz_test_draft"]

        def bad_preview(args):
            self.env["res.partner.category"].sudo().create({"name": "from-preview"})
            return {"summary": "x", "lines": []}

        from unittest.mock import patch

        with patch.object(
            type(toolbox), "_xtd_ai_preview_zz_test_draft", lambda s, a: bad_preview(a)
        ):
            toolbox._xtd_ai_preview(tool, {"name": "a"})
        self.assertEqual(self.tag_count("from-preview"), 0)

    def test_tool_failure_rolls_back_partial_writes(self):
        from unittest.mock import patch

        toolbox_cls = type(self.env["xtd.ai.toolbox.test"])

        def failing(self_, args):
            self_.env["res.partner.category"].create({"name": "half-done"})
            raise UserError(self_.env._("boom"))

        self.set_confirm(self.user, False)
        with patch.object(toolbox_cls, "tool_zz_test_draft", failing):
            result = self.call(self.user, self.run, "zz_test_draft", {"name": "x"})
        self.assertEqual(result["structuredContent"]["error"]["code"], "validation")
        self.assertEqual(self.tag_count("half-done"), 0)
