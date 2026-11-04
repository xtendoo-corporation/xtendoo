from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from odoo.tools import mute_logger

from ..tools.errors import XtdAiToolError
from .common import AI_GROUPS, XtdAiCase


@tagged("post_install", "-at_install")
class TestPolicyGuard(XtdAiCase):
    """The gateway fails closed when a policy breaks (risk 1) and rules each
    call by the company of its document, not the first active one (risk 3)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.multi = new_test_user(
            cls.env,
            "xtd_ai_policy_multi",
            groups=AI_GROUPS + ",base.group_partner_manager",
            company_id=cls.company.id,
            company_ids=[Command.set((cls.company | cls.company2).ids)],
        )

    def setUp(self):
        super().setUp()
        self.set_confirm(self.user, False)
        self.set_confirm(self.multi, False)
        (self.company | self.company2).write(
            {"xtd_ai_profile": "balanced", "xtd_ai_paused": False}
        )
        self.both = [self.company.id, self.company2.id]

    @contextmanager
    def hooked(self, tool_name, key, method):
        """Give the test tool ``tool_name`` a ``policy`` or ``company`` method."""
        meta = self.env["xtd.ai.toolbox"]._xtd_ai_tools()[tool_name]
        cls = type(self.env[meta["model"]])
        attr = f"_xtd_ai_hook_{key}"
        with (
            patch.dict(meta, {key: attr}),
            patch.object(cls, attr, method, create=True),
        ):
            yield

    def draft(self, user, run, name, **kw):
        return self.call(user, run, "zz_test_draft", {"name": name}, **kw)[
            "structuredContent"
        ]

    def tag(self, name):
        return self.env["res.partner.category"].search([("name", "=", name)])

    # ------------------------------------------------------------------
    # Risk 1: fail closed
    # ------------------------------------------------------------------
    @mute_logger("odoo.addons.xtd_ai.models.xtd_ai_toolbox")
    def test_policy_returning_garbage_is_refused(self):
        run, _token = self.start_run()
        for value in (None, "", "n1", "N9", 1, ["N1"], {"level": "N1"}):
            with self.hooked("zz_test_draft", "policy", lambda self, args, v=value: v):
                res = self.draft(self.user, run, f"G-{value!r}")
            self.assertEqual(res["status"], "error", value)
            self.assertEqual(res["error"]["code"], "policy_error", value)
            self.assertIn("no se hace", res["error"]["message"])
            self.assertFalse(self.tag(f"G-{value!r}"), value)
        audits = self.audits(run, tool_name="zz_test_draft")
        self.assertEqual(set(audits.mapped("outcome")), {"denied"})
        self.assertEqual(set(audits.mapped("error_code")), {"policy_error"})
        self.assertFalse(
            self.env["xtd.ai.pending_action"].search([("run_id", "=", run.id)])
        )

    @mute_logger("odoo.addons.xtd_ai.models.xtd_ai_toolbox")
    def test_policy_raising_is_refused(self):
        def boom(self, args):
            raise KeyError("lines")

        run, _token = self.start_run()
        with self.hooked("zz_test_draft", "policy", boom):
            res = self.draft(self.user, run, "Boom")
        self.assertEqual(res["error"]["code"], "policy_error", res)
        self.assertFalse(self.tag("Boom"))
        audit = self.audits(run, tool_name="zz_test_draft")
        self.assertEqual(audit.outcome, "denied")
        self.assertEqual(audit.error_code, "policy_error")

    def test_policy_business_errors_keep_their_message(self):
        def not_found(self, args):
            raise XtdAiToolError("not_found", "No se ha encontrado «X».")

        run, _token = self.start_run()
        with self.hooked("zz_test_draft", "policy", not_found):
            res = self.draft(self.user, run, "NF")
        self.assertEqual(res["error"]["code"], "not_found", res)
        self.assertFalse(self.tag("NF"))

    def test_valid_policy_levels_still_work(self):
        run, _token = self.start_run()
        with self.hooked("zz_test_draft", "policy", lambda self, args: "N1"):
            self.assertEqual(self.draft(self.user, run, "V1")["status"], "ok")
        with self.hooked("zz_test_draft", "policy", lambda self, args: "N2"):
            res = self.draft(self.user, run, "V2")
        self.assertEqual(res["status"], "pending_confirmation", res)
        with self.hooked("zz_test_draft", "policy", lambda self, args: "N4"):
            res = self.draft(self.user, run, "V4")
        self.assertEqual(res["error"]["code"], "forbidden", res)

    @mute_logger("odoo.addons.xtd_ai.models.xtd_ai_mcp")
    def test_invalid_level_from_an_override_is_refused(self):
        """Even if an override of ``_xtd_ai_call_level`` returns garbage, the
        gateway never executes the call (only N0/N1 run directly)."""
        run, _token = self.start_run()
        cls = type(self.env["xtd.ai.toolbox"])
        with patch.object(cls, "_xtd_ai_call_level", return_value="N7"):
            res = self.draft(self.user, run, "Override")
        self.assertEqual(res["error"]["code"], "policy_error", res)
        self.assertFalse(self.tag("Override"))

    # ------------------------------------------------------------------
    # Risk 3: company of the document
    # ------------------------------------------------------------------
    def test_unknown_document_company_takes_the_strictest_active_one(self):
        self.company2.xtd_ai_profile = "prudent"
        run, _token = self.start_run(self.multi)
        res = self.draft(self.multi, run, "S1", cids=self.both)
        self.assertEqual(res["status"], "pending_confirmation", res)
        # with only the balanced company active, it is done
        res = self.draft(self.multi, run, "S2", cids=[self.company.id])
        self.assertEqual(res["status"], "ok", res)

    def test_document_company_rules_profile_both_ways(self):
        run, _token = self.start_run(self.multi)
        company2 = self.company2
        with self.hooked(
            "zz_test_draft",
            "company",
            lambda self, args: self.env["res.company"].browse(company2.id),
        ):
            self.company2.xtd_ai_profile = "prudent"
            res = self.draft(self.multi, run, "D1", cids=self.both)
            self.assertEqual(res["status"], "pending_confirmation", res)
            # prudent context company, balanced document company: done
            self.company.xtd_ai_profile = "prudent"
            self.company2.xtd_ai_profile = "balanced"
            res = self.draft(self.multi, run, "D2", cids=self.both)
            self.assertEqual(res["status"], "ok", res)
        audit = self.audits(run, tool_name="zz_test_draft", outcome="ok")
        self.assertEqual(audit.company_id, self.company2)

    def test_document_company_pause_and_fiscal_brake(self):
        run, _token = self.start_run(self.multi)
        company2 = self.company2
        with self.hooked(
            "zz_test_draft",
            "company",
            lambda self, args: self.env["res.company"].browse(company2.id),
        ):
            self.company2.xtd_ai_paused = True
            res = self.draft(self.multi, run, "P1", cids=self.both)
            self.assertEqual(res["error"]["code"], "paused", res)
            self.company2.xtd_ai_paused = False
            self.assertEqual(
                self.draft(self.multi, run, "P2", cids=self.both)["status"], "ok"
            )
        # the fiscal brake is read from the document company too
        company_cls = type(self.env["res.company"])
        brake = company_cls._xtd_ai_has_fiscal_reporting

        def fiscal(company):
            return company.id == company2.id or brake(company)

        meta = self.env["xtd.ai.toolbox"]._xtd_ai_tools()["zz_test_draft"]
        toolbox = (
            self.env["xtd.ai.toolbox"]
            .with_user(self.multi)
            .with_context(allowed_company_ids=self.both, xtd_ai_run=run.id)
        )
        with (
            patch.object(company_cls, "_xtd_ai_has_fiscal_reporting", fiscal),
            patch.dict(meta, {"op_class": "send_external", "skill": "contabilidad"}),
        ):
            levels = [
                toolbox._xtd_ai_call_level(meta, {"name": "F"}, company)
                for company in (self.company, self.company2)
            ]
        self.assertEqual(levels, ["N2", "N3"])

    def test_document_company_must_be_active_in_the_run(self):
        run, _token = self.start_run(self.multi)
        company2 = self.company2
        with self.hooked(
            "zz_test_draft",
            "company",
            lambda self, args: self.env["res.company"].browse(company2.id),
        ):
            res = self.draft(self.multi, run, "A1", cids=[self.company.id])
        self.assertEqual(res["error"]["code"], "forbidden", res)
        self.assertIn(self.company2.name, res["error"]["message"])
        self.assertFalse(self.tag("A1"))

    @mute_logger("odoo.addons.xtd_ai.models.xtd_ai_toolbox")
    def test_company_method_returning_garbage_is_refused(self):
        run, _token = self.start_run(self.multi)
        with self.hooked("zz_test_draft", "company", lambda self, args: "AI other"):
            res = self.draft(self.multi, run, "C1", cids=self.both)
        self.assertEqual(res["error"]["code"], "policy_error", res)
        self.assertFalse(self.tag("C1"))
