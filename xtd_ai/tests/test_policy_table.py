import importlib.util

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import file_path, mute_logger

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestPolicyTable(XtdAiCase):
    """Profiles and policy table per company (ANALISIS_PERMISOS §6.1)."""

    def policy(self, company=None):
        return self.env["xtd.ai.policy"].with_company(company or self.company)

    def rule(self, **vals):
        rules = self.env["xtd.ai.policy.rule"]
        key = "op_class" if vals.get("op_class") else "tool_name"
        row = rules.search(
            [("company_id", "=", self.company.id), (key, "=", vals[key])]
        )
        if row:
            row.write(vals)
            return row
        return rules.create({"company_id": self.company.id} | vals)

    def test_balanced_by_default_and_profile_per_company(self):
        self.company.xtd_ai_profile = False
        self.assertEqual(self.policy()._xtd_ai_level("create_draft"), "N1")
        self.company.xtd_ai_profile = "prudent"
        self.assertEqual(self.policy()._xtd_ai_level("create_draft"), "N2")
        self.assertEqual(self.policy(self.company2)._xtd_ai_level("create_draft"), "N1")
        self.company.xtd_ai_profile = "agile"
        self.assertEqual(self.policy()._xtd_ai_level("transition"), "N2")

    def test_global_parameter_still_applies_without_company_value(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("xtd_ai.policy.profile", "prudent")
        self.company.xtd_ai_profile = False
        self.assertEqual(self.policy()._xtd_ai_level("edit_low"), "N2")
        self.company.xtd_ai_profile = "balanced"
        self.assertEqual(self.policy()._xtd_ai_level("edit_low"), "N1")
        # a legacy level parameter still hardens, never opens
        params.set_param("xtd_ai.policy.level.edit_low", "N3")
        self.assertEqual(self.policy()._xtd_ai_level("edit_low"), "N3")

    def test_table_hardens_and_relaxes_down_to_the_floor(self):
        self.company.xtd_ai_profile = "balanced"
        self.assertEqual(self.policy()._xtd_ai_level("transition"), "N3")
        row = self.rule(op_class="transition", level="N2")
        self.assertEqual(self.policy()._xtd_ai_level("transition"), "N2")
        row.level = "N4"
        self.assertEqual(self.policy()._xtd_ai_level("transition"), "N4")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            row.level = "N1"  # below Ágil
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.rule(op_class="transition_internal", level="N1")
        self.assertEqual(self.policy(self.company2)._xtd_ai_level("transition"), "N3")

    @mute_logger("odoo.sql_db")
    def test_publish_and_red_lines_are_not_editable(self):
        for op_class, level in (
            ("post", "N2"),
            ("post", "N1"),
            ("payment", "N3"),
            ("admin", "N1"),
        ):
            with self.assertRaises(ValidationError, msg=op_class), self.cr.savepoint():
                self.rule(op_class=op_class, level=level)
        self.assertEqual(self.policy()._xtd_ai_level("post"), "N3")
        self.assertEqual(self.policy()._xtd_ai_level("payment"), "N4")
        self.env["xtd.ai.policy.rule"]._xtd_ai_ensure_rows(self.company)
        rows = self.env["xtd.ai.policy.rule"].search(
            [
                ("company_id", "=", self.company.id),
                ("op_class", "in", ("post", "admin")),
            ]
        )
        self.assertEqual(len(rows), 2)
        self.assertFalse(any(rows.mapped("editable")))
        self.assertEqual(set(rows.mapped("effective_level")), {"N3", "N4"})

    def test_tool_row_only_hardens(self):
        run, _token = self.start_run()
        self.set_confirm(self.user, False)
        res = self.call(self.user, run, "zz_test_draft", {"name": "T1"})
        self.assertEqual(res["structuredContent"]["status"], "ok")
        self.rule(tool_name="zz_test_draft", level="N2")
        res = self.call(self.user, run, "zz_test_draft", {"name": "T2"})
        self.assertEqual(res["structuredContent"]["status"], "pending_confirmation")
        self.env["xtd.ai.policy.rule"].search(
            [("tool_name", "=", "zz_test_draft")]
        ).unlink()
        self.rule(tool_name="zz_test_create", level="N1")
        res = self.call(self.user, run, "zz_test_create", {"name": "T3"})
        self.assertEqual(res["structuredContent"]["status"], "pending_confirmation")

    def test_settings_write_the_company(self):
        settings = self.env["res.config.settings"].create({})
        settings.xtd_ai_profile = "prudent"
        settings.xtd_ai_discount_threshold = 20
        settings.xtd_ai_purchase_confirm_limit = 500
        settings.execute()
        self.assertEqual(self.company.xtd_ai_profile, "prudent")
        self.assertEqual(self.policy()._xtd_ai_discount_threshold(), 20)
        self.assertEqual(self.policy()._xtd_ai_purchase_confirm_limit(), 500)
        self.assertEqual(self.policy(self.company2)._xtd_ai_discount_threshold(), 15)
        action = settings.action_xtd_ai_policy_table()
        self.assertEqual(action["res_model"], "xtd.ai.policy.rule")

    def test_migration_moves_the_parameters(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("xtd_ai.policy.profile", "agile")
        params.set_param("xtd_ai.policy.discount_threshold", "12")
        params.set_param("xtd_ai.policy.level.edit_money", "N3")
        params.set_param("xtd_ai.policy.level.create_draft", "N1")  # no-op
        params.set_param("xtd_ai.policy.level.post", "N1")  # never opens
        self.env["res.company"].search([]).write({"xtd_ai_profile": False})
        path = file_path("xtd_ai/migrations/19.0.2.10.0/post-migrate.py")
        spec = importlib.util.spec_from_file_location("xtd_ai_mig_2_10", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.2.9.0")
        self.assertEqual(self.company.xtd_ai_profile, "agile")
        self.assertEqual(self.company.xtd_ai_discount_threshold, 12)
        rows = {
            r.op_class: r.level
            for r in self.env["xtd.ai.policy.rule"].search(
                [("company_id", "=", self.company.id)]
            )
        }
        self.assertEqual(rows["edit_money"], "N3")
        self.assertFalse(rows["create_draft"])
        self.assertFalse(rows["post"])
        self.assertEqual(self.policy()._xtd_ai_level("post"), "N3")
