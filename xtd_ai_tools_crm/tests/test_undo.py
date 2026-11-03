from odoo.tests import tagged

from .common import XtdAiCrmCase


@tagged("post_install", "-at_install")
class TestCrmUndo(XtdAiCrmCase):
    def opportunity(self, user):
        self.direct(user)
        res = self.sc(
            user,
            "create_opportunity",
            {"name": "Para deshacer", "partner": "Cliente Alfa SL"},
        )
        self.assertEqual(res["status"], "ok", res)
        return self.env["crm.lead"].browse(res["records"][0]["id"])

    def test_manager_deletes_and_salesman_archives(self):
        lead = self.opportunity(self.sales_manager)
        undo = self.env["xtd.ai.undo"].with_user(self.sales_manager)
        self.assertEqual(undo._xtd_ai_undo("crm.lead", lead.id)["mode"], "unlink")
        self.assertFalse(lead.exists())
        lead = self.opportunity(self.salesman)
        undo = self.env["xtd.ai.undo"].with_user(self.salesman)
        self.assertEqual(
            undo._xtd_ai_undo("crm.lead", lead.id), {"undone": True, "mode": "archive"}
        )
        self.assertFalse(lead.active)
        self.assertEqual(undo._xtd_ai_undo_state("crm.lead", lead.id), "undone")

    def test_another_salesman_cannot_undo_it(self):
        lead = self.opportunity(self.salesman)
        result = (
            self.env["xtd.ai.undo"]
            .with_user(self.sales_manager)
            ._xtd_ai_undo("crm.lead", lead.id)
        )
        self.assertFalse(result["undone"])  # created by someone else
        self.assertTrue(lead.active)
