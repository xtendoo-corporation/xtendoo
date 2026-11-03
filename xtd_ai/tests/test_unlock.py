from unittest.mock import patch

from odoo.tests import tagged

from ..tools import is_unlocked, unlock
from ..tools.errors import XtdAiDraftOnlyError
from ..tools.unlock import GRANT_KEY, UNLOCK_KEY
from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestUnlockPerTool(XtdAiCase):
    """A confirmed tool lifts only the guard it declares, for one record (§6.5)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.p1 = cls.env["res.partner"].create({"name": "Unlock Uno"})
        cls.p2 = cls.env["res.partner"].create({"name": "Unlock Dos"})

    def propose_and_confirm(self, attack, other=None):
        run, _token = self.start_run()
        args = {"partner_id": self.p1.id, "attack": attack}
        if other:
            args["other_id"] = other.id
        res = self.call(self.user, run, "zz_test_unlock", args)["structuredContent"]
        self.assertEqual(res["status"], "pending_confirmation", res)
        action = self.env["xtd.ai.pending_action"].browse(res["pending_action_id"])
        self.assertEqual(action.preview["summary"], "unlock in preview: no")
        action.with_user(self.user).action_confirm()
        run.state = "done"
        return action

    def notes(self, partner):
        return self.env["mail.message"].search_count(
            [("model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )

    def test_confirmed_tool_posts_its_note(self):
        before = self.notes(self.p1)
        action = self.propose_and_confirm("none")
        self.assertEqual(action.state, "confirmed", action.error)
        self.assertEqual(self.notes(self.p1), before + 1)

    def test_unlock_does_not_reach_another_record(self):
        before = self.notes(self.p2)
        action = self.propose_and_confirm("other_record", self.p2)
        self.assertEqual(action.state, "failed")
        self.assertEqual(self.notes(self.p2), before)

    def test_unlock_does_not_open_other_operations_or_email(self):
        for attack in ("other_op", "comment", "undeclared"):
            before = self.notes(self.p1)
            action = self.propose_and_confirm(attack)
            self.assertEqual(action.state, "failed", attack)
            # the savepoint rolled the whole execution back
            self.assertEqual(self.notes(self.p1), before, attack)

    def test_grant_is_only_set_by_the_gateway(self):
        run, _token = self.start_run()
        env = self.tool_env(self.user, run)
        partner = env["res.partner"].browse(self.p1.id)
        with self.assertRaises(XtdAiDraftOnlyError):
            unlock(partner, "message_post")
        # a forged unlock key without the grant opens nothing
        forged = partner.with_context(
            **{UNLOCK_KEY: ("res.partner.message_post", self.p1.id)}
        )
        self.assertFalse(is_unlocked(forged, "message_post"))
        with self.assertRaises(XtdAiDraftOnlyError):
            forged.message_post(
                body="x", message_type="comment", subtype_xmlid="mail.mt_note"
            )
        # the grant of one operation does not unlock another one or a recordset
        granted = partner.with_context(**{GRANT_KEY: ("res.partner.message_post",)})
        with self.assertRaises(XtdAiDraftOnlyError):
            unlock(granted, "message_notify")
        both = granted.browse((self.p1 | self.p2).ids)
        with self.assertRaises(XtdAiDraftOnlyError):
            unlock(both, "message_post")

    def test_tool_without_unlocks_runs_without_grant(self):
        run, _token = self.start_run()
        env = self.tool_env(self.user, run)
        grant = {GRANT_KEY: ("res.partner.message_post",)}
        env = env(context=dict(env.context) | grant)
        toolbox = env["xtd.ai.toolbox"]
        tool = toolbox._xtd_ai_tools()["zz_test_env"]
        seen = {}
        original = type(env["xtd.ai.toolbox.test"]).tool_zz_test_env

        def spy(self_, args):
            seen["grant"] = self_.env.context.get(GRANT_KEY)
            return original(self_, args)

        with patch.object(type(env["xtd.ai.toolbox.test"]), "tool_zz_test_env", spy):
            toolbox._xtd_ai_execute(tool, {})
        self.assertEqual(seen["grant"], ())
