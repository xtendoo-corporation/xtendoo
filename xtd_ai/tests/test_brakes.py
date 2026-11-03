from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestSafetyBrakes(XtdAiCase):
    """Rate limits, pause switch and Veri*Factu / SII brake (§6.4)."""

    def setUp(self):
        super().setUp()
        self.set_confirm(self.user, False)
        self.company.write(
            {"xtd_ai_max_writes_hour": 60, "xtd_ai_max_writes_message": 15}
        )

    def status(self, run, name, args):
        return self.call(self.user, run, name, args)["structuredContent"]

    def assert_ok(self, run, name, args):
        self.assertEqual(self.status(run, name, args)["status"], "ok", name)

    def test_pause_stops_new_and_running_requests(self):
        run, _token = self.start_run()
        self.company.xtd_ai_paused = True
        res = self.status(run, "zz_test_echo", {"text": "x"})
        self.assertEqual(res["error"]["code"], "paused")
        run.state = "done"
        with self.assertRaises(UserError):
            self.start_run()
        self.company.xtd_ai_paused = False
        run2, _token = self.start_run()
        self.assertEqual(
            self.status(run2, "zz_test_echo", {"text": "x"})["status"], "ok"
        )

    def test_writes_per_message(self):
        self.company.xtd_ai_max_writes_message = 2
        run, _token = self.start_run()
        for name in ("R1", "R2"):
            self.assertEqual(
                self.status(run, "zz_test_draft", {"name": name})["status"], "ok"
            )
        res = self.status(run, "zz_test_draft", {"name": "R3"})
        self.assertEqual(res["error"]["code"], "rate_limited")
        tags = self.env["res.partner.category"]
        self.assertFalse(tags.search([("name", "=", "R3")]))
        # cards count too, reads are never limited
        self.assertEqual(
            self.status(run, "zz_test_create", {"name": "R4"})["error"]["code"],
            "rate_limited",
        )
        self.assertEqual(
            self.status(run, "zz_test_echo", {"text": "x"})["status"], "ok"
        )

    def test_writes_per_hour_and_user(self):
        self.company.write(
            {"xtd_ai_max_writes_hour": 2, "xtd_ai_max_writes_message": 0}
        )
        run, _token = self.start_run()
        self.status(run, "zz_test_draft", {"name": "H1"})
        run.state = "done"
        run2, _token = self.start_run()
        self.status(run2, "zz_test_create", {"name": "H2"})
        res = self.status(run2, "zz_test_draft", {"name": "H3"})
        self.assertEqual(res["error"]["code"], "rate_limited")
        # another user has their own budget
        run2.state = "done"
        self.set_confirm(self.user2, False)
        run3, _token = self.start_run(self.user2)
        res = self.call(self.user2, run3, "zz_test_draft", {"name": "H4"})
        # (user2 may not create tags: what matters is that no limit applies)
        error = res["structuredContent"].get("error") or {}
        self.assertNotEqual(error.get("code"), "rate_limited")
        # 0 means no limit
        self.company.xtd_ai_max_writes_hour = 0
        run3.state = "done"
        run4, _token = self.start_run()
        self.assertEqual(
            self.status(run4, "zz_test_draft", {"name": "H5"})["status"], "ok"
        )

    def test_fiscal_brake_keeps_invoices_in_n3(self):
        policy = self.env["xtd.ai.policy"]
        invoice_tool = {"name": "x", "op_class": "transition", "skill": "contabilidad"}
        sale_tool = {"name": "y", "op_class": "transition", "skill": "ventas"}
        self.company.xtd_ai_profile = "agile"
        self.assertEqual(policy._xtd_ai_tool_brakes(invoice_tool, "N2"), "N2")
        company_cls = type(self.env["res.company"])
        with patch.object(
            company_cls, "_xtd_ai_has_fiscal_reporting", return_value=True
        ):
            for op_class in ("transition", "send_external", "post"):
                tool = invoice_tool | {"op_class": op_class}
                self.assertEqual(policy._xtd_ai_tool_brakes(tool, "N1"), "N3")
            self.assertEqual(policy._xtd_ai_tool_brakes(sale_tool, "N2"), "N2")
            self.assertEqual(
                policy._xtd_ai_tool_brakes(
                    invoice_tool | {"op_class": "edit_low"}, "N1"
                ),
                "N1",
            )
            self.assertTrue(self.company.with_context(test=1).xtd_ai_fiscal_brake)

    def test_fiscal_detection_by_installed_fields(self):
        company = self.company
        expected = bool(
            (
                "l10n_es_edi_verifactu_required" in company._fields
                and company.l10n_es_edi_verifactu_required
            )
            or (
                "l10n_es_sii_tax_agency" in company._fields
                and company.l10n_es_sii_tax_agency
            )
            or (
                "l10n_es_tbai_is_enabled" in company._fields
                and company.l10n_es_tbai_is_enabled
            )
        )
        self.assertEqual(company._xtd_ai_has_fiscal_reporting(), expected)
