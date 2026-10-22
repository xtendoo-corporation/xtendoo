from odoo.tests import tagged

from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

from .common import XtdAiCrmCase


@tagged("post_install", "-at_install")
class TestCrmGuards(XtdAiCrmCase):
    def setUp(self):
        super().setUp()
        self.run, _t = self.start_run(self.sales_manager)
        self.agent_env = self.tool_env(self.sales_manager, self.run)
        self.lead = self.env["crm.lead"].create(
            {
                "name": "Guarded opp",
                "type": "opportunity",
                "user_id": self.sales_manager.id,
            }
        )
        self.a_lead = self.agent_env["crm.lead"].browse(self.lead.id)

    def test_crm_lead_guards_block_in_run(self):
        for method in (
            "action_set_won",
            "action_set_won_rainbowman",
            "action_set_lost",
            "unlink",
        ):
            with self.assertRaises(XtdAiDraftOnlyError, msg=method):
                getattr(self.a_lead, method)()
        with self.assertRaises(XtdAiDraftOnlyError):
            self.a_lead.write(
                {
                    "stage_id": self.env["crm.stage"]
                    .search([("is_won", "=", True)], limit=1)
                    .id
                }
            )
        with self.assertRaises(XtdAiDraftOnlyError):
            self.a_lead.write({"active": False})
        self.assertTrue(self.lead.active)
        self.assertFalse(self.lead.stage_id.is_won)
        self.assertTrue(self.lead.exists())

    def test_crm_lead_normal_writes_allowed_in_run(self):
        self.a_lead.write({"expected_revenue": 123.0})
        self.assertEqual(self.lead.expected_revenue, 123.0)

    def test_crm_lead_works_outside_run(self):
        lead = self.lead.with_user(self.sales_manager)
        lead.action_set_won()
        self.assertTrue(lead.stage_id.is_won)
        lead2 = self.env["crm.lead"].create({"name": "to lose", "type": "opportunity"})
        lead2.with_user(self.sales_manager).action_set_lost()
        self.assertFalse(lead2.active)
        lead2.with_user(self.sales_manager).unlink()
        self.assertFalse(lead2.exists())
