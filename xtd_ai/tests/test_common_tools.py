from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import AI_GROUPS, XtdAiCase


@tagged("post_install", "-at_install")
class TestCommonTools(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run()

    def data(self, name, args=None, user=None, run=None):
        result = self.call(user or self.user, run or self.run, name, args or {})
        self.assertFalse(result["isError"], result)
        return result["structuredContent"]["data"]

    def test_get_user_context(self):
        data = self.data("get_user_context")
        self.assertEqual(data["user"]["id"], self.user.id)
        self.assertEqual(data["company"]["id"], self.company.id)
        self.assertEqual(
            data["allowed_companies"],
            [{"id": self.company.id, "name": self.company.name}],
        )
        self.assertIs(data["confirm_writes"], True)
        self.assertRegex(data["today"], r"^\d{4}-\d{2}-\d{2}$")

    def test_load_skill(self):
        data = self.data("load_skill", {"skill": "contactos"})
        self.assertIn("create_contact", data["instructions"])
        result = self.call(self.user, self.run, "load_skill", {"skill": "nonexistent"})
        self.assertEqual(
            result["structuredContent"]["error"]["code"], "validation"
        )  # enum violation

    def test_search_partners_and_untrusted_text(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Zeta Quimica " + "x" * 400,
                "vat": "ESB11111111",
                "city": "Sevilla",
                "email": "zeta@example.com",
            }
        )
        data = self.data("search_partners", {"query": "Zeta Quimica"})
        self.assertEqual(data["total"], 1)
        row = data["items"][0]
        self.assertEqual(row["id"], partner.id)
        self.assertEqual(row["vat"], "ESB11111111")
        self.assertEqual(len(row["name"]["untrusted_text"]), 300)
        self.assertTrue(row["name"]["truncated"])
        self.assertFalse(row["city"]["truncated"])
        by_vat = self.data("search_partners", {"query": "ESB11111111"})
        self.assertEqual([r["id"] for r in by_vat["items"]], [partner.id])
        result = self.call(self.user, self.run, "search_partners", {"query": "Zeta"})
        self.assertEqual(result["structuredContent"]["records"][0]["id"], partner.id)

    def test_search_partners_limit_and_truncation(self):
        self.env["res.partner"].create(
            [{"name": f"Bulk Partner {i}"} for i in range(5)]
        )
        data = self.data("search_partners", {"query": "Bulk Partner", "limit": 2})
        self.assertEqual(len(data["items"]), 2)
        self.assertTrue(data["truncated"])
        self.assertEqual(data["total"], 5)

    def test_search_partners_respects_record_rules(self):
        hidden = self.env["res.partner"].create(
            {"name": "Hidden Co Rulecheck", "company_id": self.company2.id}
        )
        visible = self.env["res.partner"].create(
            {"name": "Visible Co Rulecheck", "company_id": self.company.id}
        )
        restricted = new_test_user(
            self.env, "xtd_ai_restricted", groups=AI_GROUPS, company_id=self.company.id
        )
        run, _t = self.start_run(restricted)
        names = {
            r["id"]
            for r in self.data(
                "search_partners", {"query": "Co Rulecheck"}, restricted, run
            )["items"]
        }
        self.assertIn(visible.id, names)
        self.assertNotIn(hidden.id, names)
        # get_partner_summary of a hidden partner is not_found
        result = self.call(
            restricted, run, "get_partner_summary", {"partner_id": hidden.id}
        )
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"]["code"], "not_found")

    def test_get_partner_summary(self):
        partner = self.env["res.partner"].create(
            {"name": "Sumario SL", "is_company": True}
        )
        data = self.data("get_partner_summary", {"partner_id": partner.id})
        self.assertEqual(data["id"], partner.id)
        self.assertIn("totals", data)

    def test_search_products(self):
        if "product.product" not in self.env:
            self.skipTest("product not installed")
        product = self.env["product.product"].create(
            {"name": "Widget AI Test", "default_code": "WAI-1", "list_price": 12.5}
        )
        data = self.data("search_products", {"query": "WAI-1"})
        self.assertEqual(data["items"][0]["id"], product.id)
        self.assertEqual(
            data["items"][0]["list_price"],
            {"amount": 12.5, "currency": self.company.currency_id.name},
        )

    def test_create_contact_pending_with_duplicates_then_confirm(self):
        existing = self.env["res.partner"].create(
            {"name": "Duplicada SL", "vat": "ESB22222222"}
        )
        result = self.call(
            self.user,
            self.run,
            "create_contact",
            {
                "name": "Otra Duplicada SL",
                "is_company": True,
                "vat": "ESB22222222",
                "country_code": "es",
                "city": "Cadiz",
            },
        )
        structured = result["structuredContent"]
        self.assertEqual(structured["status"], "pending_confirmation")
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(structured["pending_action_id"])
        )
        self.assertEqual([d["id"] for d in action.preview["duplicates"]], [existing.id])
        self.assertIn("1", structured["summary"])
        self.assertFalse(
            self.env["res.partner"].search([("name", "=", "Otra Duplicada SL")])
        )
        # always confirmation, even when the user disabled it
        self.set_confirm(self.user, False)
        result2 = self.call(
            self.user, self.run, "create_contact", {"name": "Nueva Persona"}
        )
        self.assertEqual(result2["structuredContent"]["status"], "pending_confirmation")
        # confirm
        outcome = action.with_user(self.user).action_confirm()
        self.assertEqual(outcome["state"], "confirmed", outcome)
        created = self.env["res.partner"].search([("name", "=", "Otra Duplicada SL")])
        self.assertEqual(len(created), 1)
        self.assertEqual(
            (created.vat, created.city, created.country_id.code, created.is_company),
            ("ESB22222222", "Cadiz", "ES", True),
        )
        self.assertEqual(created.create_uid, self.user)

    def test_create_contact_no_duplicates_and_validation(self):
        structured = self.call(
            self.user, self.run, "create_contact", {"name": "Totalmente Unica"}
        )["structuredContent"]
        action = (
            self.env["xtd.ai.pending_action"]
            .sudo()
            .browse(structured["pending_action_id"])
        )
        self.assertEqual(action.preview["duplicates"], [])
        bad = self.call(
            self.user,
            self.run,
            "create_contact",
            {"name": "Pais Malo", "country_code": "ZZ"},
        )
        self.assertTrue(bad["isError"])
        self.assertEqual(bad["structuredContent"]["error"]["code"], "validation")
        bad = self.call(self.user, self.run, "create_contact", {"name": "X"})
        self.assertEqual(bad["structuredContent"]["error"]["code"], "validation")

    def test_create_contact_requires_partner_manager_group(self):
        run2, _t = self.start_run(self.user2)
        status, response = self.rpc(
            self.user2,
            run2,
            "tools/call",
            {"name": "create_contact", "arguments": {"name": "No Debe"}},
        )
        self.assertEqual((status, response["error"]["code"]), (200, -32601))

    def test_resolve_helper(self):
        toolbox = self.tool_env(self.user, self.run)["xtd.ai.toolbox"]
        a = self.env["res.partner"].create({"name": "Resolver Alpha"})
        self.env["res.partner"].create({"name": "Resolver Alphabet"})
        self.assertEqual(toolbox._xtd_ai_resolve("res.partner", a.id), a)
        self.assertEqual(toolbox._xtd_ai_resolve("res.partner", str(a.id)), a)
        self.assertEqual(
            toolbox._xtd_ai_resolve("res.partner", "resolver alpha"), a
        )  # exact wins
        from ..tools.errors import XtdAiToolError

        with self.assertRaises(XtdAiToolError) as ctx:
            toolbox._xtd_ai_resolve("res.partner", "Resolver Alph")
        self.assertEqual(ctx.exception.code, "ambiguous")
        self.assertEqual(len(ctx.exception.data["candidates"]), 2)
        with self.assertRaises(XtdAiToolError) as ctx:
            toolbox._xtd_ai_resolve("res.partner", "no such partner at all")
        self.assertEqual(ctx.exception.code, "not_found")

    def test_text_money_helpers(self):
        toolbox = self.env["xtd.ai.toolbox"]
        self.assertEqual(
            toolbox._xtd_ai_text("a" * 301),
            {"untrusted_text": "a" * 300, "truncated": True},
        )
        self.assertEqual(
            toolbox._xtd_ai_text("ab"), {"untrusted_text": "ab", "truncated": False}
        )
        self.assertIsNone(toolbox._xtd_ai_text(False))
        self.assertEqual(
            toolbox._xtd_ai_money(1.005, "EUR"), {"amount": 1.0, "currency": "EUR"}
        )
        eur = self.company.currency_id
        self.assertEqual(
            toolbox._xtd_ai_money(123.456, eur)["amount"],
            round(123.456, eur.decimal_places),
        )
        self.assertEqual(
            (
                toolbox._xtd_ai_limit(),
                toolbox._xtd_ai_limit(0),
                toolbox._xtd_ai_limit(999),
            ),
            (50, 1, 200),
        )
