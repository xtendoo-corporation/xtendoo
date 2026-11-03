from odoo.exceptions import AccessError
from odoo.tests import tagged

from ..tools import is_unlocked, unlock, unlocked_record
from ..tools.errors import XtdAiDraftOnlyError
from ..tools.unlock import GRANT_KEY
from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestUsageReport(XtdAiCase):
    """§6.4.8: weekly cards per tool, read-only, for AI managers."""

    def cards(self, tool, states):
        run, _token = self.start_run()
        actions = self.env["xtd.ai.pending_action"].sudo()
        for state in states:
            actions.create(
                {
                    "run_id": run.id,
                    "conversation_id": run.conversation_id.id,
                    "user_id": self.user.id,
                    "tool_name": tool,
                    "arguments": {},
                    "preview": {"summary": "x"},
                    "state": state,
                }
            )
        run.state = "done"

    def rows(self, tool):
        return (
            self.env["xtd.ai.usage.report"]
            .with_user(self.manager)
            .search([("tool_name", "=", tool)])
        )

    def test_counts_and_flags(self):
        self.cards("zz_good", ["confirmed"] * 20)
        self.cards("zz_bad", ["confirmed"] * 3 + ["cancelled"] * 2 + ["expired"])
        self.env.flush_all()
        good, bad = self.rows("zz_good"), self.rows("zz_bad")
        self.assertEqual(sum(good.mapped("accepted")), 20)
        self.assertTrue(all(good.mapped("candidate_n1")))
        self.assertFalse(any(good.mapped("needs_improvement")))
        self.assertEqual(sum(bad.mapped("rejected")), 2)
        self.assertEqual(sum(bad.mapped("expired")), 1)
        self.assertTrue(any(bad.mapped("needs_improvement")))
        self.assertFalse(any(bad.mapped("candidate_n1")))

    def test_few_cards_flag_nothing(self):
        self.cards("zz_few", ["confirmed"] * 2)
        self.env.flush_all()
        row = self.rows("zz_few")
        self.assertFalse(row.candidate_n1 or row.needs_improvement)

    def test_users_cannot_read_it(self):
        with self.assertRaises(AccessError):
            self.env["xtd.ai.usage.report"].with_user(self.user).search([])


@tagged("post_install", "-at_install")
class TestUnlockSeveral(XtdAiCase):
    """unlock(record, a, b): both guards, the same record, both granted."""

    def test_several_methods(self):
        partner = self.env["res.partner"].create({"name": "Multi"})
        other = self.env["res.partner"].create({"name": "Otro"})
        env = self.env(user=self.user.id, su=False)
        granted = (
            env["res.partner"]
            .browse(partner.id)
            .with_context(**{GRANT_KEY: ("res.partner.a", "res.partner.b")})
        )
        both = unlock(granted, "a", "b")
        self.assertTrue(is_unlocked(both, "a") and is_unlocked(both, "b"))
        self.assertFalse(is_unlocked(both, "c"))
        self.assertFalse(is_unlocked(both.browse(other.id), "a"))
        self.assertEqual(unlocked_record(both.env, "b"), ("res.partner", partner.id))
        self.assertIsNone(unlocked_record(both.env, "c"))
        with self.assertRaises(XtdAiDraftOnlyError):
            unlock(granted, "a", "c")  # "c" not granted to the running tool
