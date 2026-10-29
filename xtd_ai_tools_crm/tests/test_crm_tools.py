from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import INJECTION, XtdAiCrmCase

CRM_TOOLS = {
    "search_opportunities",
    "get_opportunity",
    "pipeline_report",
    "create_opportunity",
}


@tagged("post_install", "-at_install")
class TestCrmTools(XtdAiCrmCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.team = env["crm.team"].create({"name": "Equipo Norte XT"})
        cls.team2 = env["crm.team"].create({"name": "Equipo Sur XT"})
        stages = env["crm.stage"].search([], order="sequence, id")
        cls.stage_new = stages[0]
        cls.stage_other = env["crm.stage"].create(
            {"name": "Propuesta XT", "sequence": 50}
        )
        cls.stage_won = env["crm.stage"].search([("is_won", "=", True)], limit=1)
        today = fields.Date.today()
        cls.lead1 = cls.lead(
            "Opp Alfa",
            cls.salesman,
            partner=cls.partner,
            revenue=1000,
            prob=50,
            deadline=today + timedelta(days=10),
            stage=cls.stage_new,
            team=cls.team,
        )
        cls.lead2 = cls.lead(
            "Opp Beta",
            cls.salesman2,
            partner=cls.partner_b,
            revenue=5000,
            prob=20,
            deadline=today + timedelta(days=40),
            stage=cls.stage_other,
            team=cls.team2,
        )
        cls.lead_won = cls.lead(
            "Opp Ganada", cls.salesman, revenue=700, stage=cls.stage_won, team=cls.team
        )
        cls.lead_lost = cls.lead(
            "Opp Perdida", cls.salesman, revenue=300, team=cls.team
        )
        cls.lead_lost.action_archive()
        cls.lead_lost.write({"probability": 0})

    @classmethod
    def lead(
        cls,
        name,
        user,
        partner=None,
        revenue=0,
        prob=None,
        deadline=None,
        stage=None,
        team=None,
    ):
        vals = {
            "name": name,
            "type": "opportunity",
            "user_id": user.id,
            "expected_revenue": revenue,
        }
        if partner:
            vals["partner_id"] = partner.id
        if prob is not None:
            vals["probability"] = prob
        if deadline:
            vals["date_deadline"] = deadline
        if stage:
            vals["stage_id"] = stage.id
        if team:
            vals["team_id"] = team.id
        return cls.env["crm.lead"].create(vals)

    def names(self, res):
        self.assertEqual(res["status"], "ok", res)
        return {r["name"]["untrusted_text"] for r in res["data"]["items"]}

    # -- reads ---------------------------------------------------------------
    def test_tool_schemas_and_kinds(self):
        run, _t = self.start_run(self.salesman)
        _status, response = self.rpc(self.salesman, run, "tools/list", {})
        tools = {t["name"]: t for t in response["result"]["tools"]}
        self.assertTrue(CRM_TOOLS <= set(tools))
        kinds = {n: tools[n]["annotations"]["xtdKind"] for n in CRM_TOOLS}
        self.assertEqual(
            {n for n, k in kinds.items() if k == "draft"}, {"create_opportunity"}
        )
        for name in CRM_TOOLS:
            schema = tools[name]["inputSchema"]
            self.assertIs(schema["additionalProperties"], False, name)
            self.assertIn("required", schema, name)

    def test_search_respects_own_documents(self):
        names = self.names(self.sc(self.salesman, "search_opportunities"))
        self.assertIn("Opp Alfa", names)
        self.assertNotIn("Opp Beta", names)
        self.assertNotIn("Opp Ganada", names)  # open by default
        self.assertNotIn("Opp Perdida", names)
        manager_names = self.names(self.sc(self.sales_manager, "search_opportunities"))
        self.assertLessEqual({"Opp Alfa", "Opp Beta"}, manager_names)

    def test_search_status_and_filters(self):
        def search(user=self.sales_manager, **args):
            return self.names(self.sc(user, "search_opportunities", args))

        self.assertEqual(
            search(status="won") & {"Opp Ganada", "Opp Alfa"}, {"Opp Ganada"}
        )
        self.assertEqual(
            search(status="lost") & {"Opp Perdida", "Opp Alfa"}, {"Opp Perdida"}
        )
        self.assertTrue(
            {"Opp Alfa", "Opp Ganada", "Opp Perdida"} <= search(status="all")
        )
        self.assertEqual(search(stage="Propuesta XT"), {"Opp Beta"})
        self.assertEqual(search(team="Equipo Norte XT"), {"Opp Alfa"})
        self.assertEqual(search(partner="Cliente Beta"), {"Opp Beta"})
        self.assertEqual(search(salesperson=self.salesman2.name), {"Opp Beta"})
        self.assertEqual(
            search(min_revenue=2000) & {"Opp Alfa", "Opp Beta"}, {"Opp Beta"}
        )
        self.assertEqual(
            search(max_revenue=2000) & {"Opp Alfa", "Opp Beta"}, {"Opp Alfa"}
        )
        today = fields.Date.today()
        window = search(
            deadline_from=str(today + timedelta(days=30)),
            deadline_to=str(today + timedelta(days=50)),
        )
        self.assertIn("Opp Beta", window)
        self.assertNotIn("Opp Alfa", window)
        res = self.sc(
            self.sales_manager, "search_opportunities", {"stage": "zzz-no-stage"}
        )
        self.assertEqual(res["error"]["code"], "not_found")

    def test_get_opportunity_and_injection(self):
        lead = self.lead("Opp Trampa", self.salesman, revenue=10)
        lead.description = f"<p>{INJECTION}</p>"
        lead.contact_name = INJECTION
        res = self.sc(self.salesman, "get_opportunity", {"opportunity": str(lead.id)})
        self.assertEqual(res["status"], "ok", res)
        data = res["data"]
        self.assertEqual(data["description"]["untrusted_text"], INJECTION)
        self.assertEqual(data["contact_name"]["untrusted_text"], INJECTION)
        self.assertEqual(data["status"], "open")
        self.assertEqual(res["records"][0]["model"], "crm.lead")
        # somebody else's opportunity is invisible
        res = self.sc(
            self.salesman, "get_opportunity", {"opportunity": str(self.lead2.id)}
        )
        self.assertEqual(res["error"]["code"], "not_found")
        # archived (lost) opportunities are readable by their owner
        res = self.sc(
            self.salesman, "get_opportunity", {"opportunity": str(self.lead_lost.id)}
        )
        self.assertEqual(res["data"]["status"], "lost")

    def test_pipeline_report(self):
        def report(user=self.sales_manager, **args):
            res = self.sc(user, "pipeline_report", args)
            self.assertEqual(res["status"], "ok", res)
            return res["data"]

        data = report(group_by="team", status="open")
        by_team = {r["team"]["name"]: r for r in data["items"] if r["team"]}
        self.assertEqual(by_team["Equipo Norte XT"]["count"], 1)
        self.assertEqual(
            by_team["Equipo Norte XT"]["expected_revenue"]["amount"], 1000.0
        )
        self.assertEqual(
            by_team["Equipo Norte XT"]["prorated_revenue"]["amount"], 500.0
        )
        self.assertEqual(by_team["Equipo Sur XT"]["prorated_revenue"]["amount"], 1000.0)
        data = report(group_by="stage")
        by_stage = {r["stage"]["name"]: r for r in data["items"] if r["stage"]}
        self.assertEqual(by_stage["Propuesta XT"]["expected_revenue"]["amount"], 5000.0)
        self.assertGreaterEqual(data["total_expected_revenue"]["amount"], 6000.0)
        data = report(group_by="salesperson")
        by_user = {
            r["salesperson"]["name"]: r for r in data["items"] if r["salesperson"]
        }
        self.assertEqual(by_user[self.salesman2.name]["count"], 1)
        # own documents: the salesman only counts his own opportunities
        own = report(self.salesman, group_by="salesperson")
        self.assertEqual(
            {r["salesperson"]["name"] for r in own["items"] if r["salesperson"]},
            {self.salesman.name},
        )
        won = report(group_by="stage", status="won")
        self.assertEqual(won["total_expected_revenue"]["amount"] >= 700.0, True)

    def test_non_sales_user_has_no_crm_tools(self):
        run, _t = self.start_run(self.nosales)
        status, response = self.rpc(
            self.nosales,
            run,
            "tools/call",
            {"name": "pipeline_report", "arguments": {}},
        )
        self.assertEqual(response["error"]["code"], -32601)

    # -- create_opportunity --------------------------------------------------
    def test_create_opportunity_direct(self):
        self.direct(self.salesman)
        res = self.sc(
            self.salesman,
            "create_opportunity",
            {
                "name": "Nueva opp",
                "partner": "Cliente Alfa SL",
                "expected_revenue": 2500,
                "probability": 30,
                "date_deadline": "2030-06-30",
                "team": "Equipo Norte XT",
                "description": "Línea 1\nLínea 2 <b>no html</b>",
            },
        )
        self.assertEqual(res["status"], "ok", res)
        lead = self.env["crm.lead"].browse(res["records"][0]["id"])
        self.assertEqual(lead.type, "opportunity")
        self.assertEqual(lead.user_id, self.salesman)
        self.assertEqual(lead.partner_id, self.partner)
        self.assertEqual(lead.expected_revenue, 2500)
        self.assertEqual(lead.probability, 30)
        self.assertEqual(lead.team_id, self.team)
        self.assertFalse(lead.stage_id.is_won)
        self.assertTrue(lead.active)
        self.assertIn("&lt;b&gt;", lead.description)  # plain text escaped, never HTML
        self.assertEqual(lead.create_uid, self.salesman)

    def test_create_opportunity_with_contact_only_and_default_salesperson(self):
        self.direct(self.salesman)
        res = self.sc(
            self.salesman,
            "create_opportunity",
            {
                "name": "Contacto nuevo",
                "contact_name": "Ana Prueba",
                "email_from": "ana@example.com",
            },
        )
        self.assertEqual(res["status"], "ok", res)
        lead = self.env["crm.lead"].browse(res["records"][0]["id"])
        self.assertEqual(
            (lead.contact_name, lead.email_from), ("Ana Prueba", "ana@example.com")
        )
        self.assertEqual(lead.user_id, self.salesman)
        self.assertFalse(lead.partner_id)

    def test_create_opportunity_salesperson_rules(self):
        self.direct(self.salesman)
        self.direct(self.sales_manager)
        res = self.sc(
            self.salesman,
            "create_opportunity",
            {"name": "Para otro", "salesperson": self.salesman2.name},
        )
        self.assertEqual(res["error"]["code"], "access_denied", res)
        res = self.sc(
            self.salesman,
            "create_opportunity",
            {"name": "Para mi", "salesperson": self.salesman.name},
        )
        self.assertEqual(res["status"], "ok", res)
        res = self.sc(
            self.sales_manager,
            "create_opportunity",
            {"name": "Asignada", "salesperson": self.salesman2.name},
        )
        self.assertEqual(res["status"], "ok", res)
        lead = self.env["crm.lead"].browse(res["records"][0]["id"])
        self.assertEqual(lead.user_id, self.salesman2)

    def test_create_opportunity_never_won_or_lost(self):
        self.direct(self.salesman)
        for extra in (
            {"stage_id": self.stage_won.id},
            {"stage": "Won"},
            {"active": False},
            {"state": "won"},
            {"type": "lead"},
        ):
            res = self.sc(
                self.salesman, "create_opportunity", dict({"name": "Trampa"}, **extra)
            )
            self.assertEqual(res["error"]["code"], "validation", extra)
        for probability in (0, 100, 150):
            res = self.sc(
                self.salesman,
                "create_opportunity",
                {"name": "Trampa", "probability": probability},
            )
            self.assertEqual(res["error"]["code"], "validation", probability)
        self.assertFalse(
            self.env["crm.lead"]
            .with_context(active_test=False)
            .search([("name", "=", "Trampa")])
        )

    def test_create_opportunity_pending_flow(self):
        self.set_confirm(self.salesman, True)
        before = self.env["crm.lead"].with_context(active_test=False).search_count([])
        res = self.sc(
            self.salesman,
            "create_opportunity",
            {
                "name": "Opp pendiente",
                "partner": str(self.partner.id),
                "expected_revenue": 900,
            },
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertIn("Opp pendiente", res["summary"])
        self.assertIn("Cliente Alfa SL", res["summary"])
        self.assertEqual(
            self.env["crm.lead"].with_context(active_test=False).search_count([]),
            before,
        )
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.salesman)
            .browse(res["pending_action_id"])
        )
        self.assertEqual(action.action_confirm()["state"], "confirmed")
        lead = self.env["crm.lead"].browse(action.result_res_id)
        self.assertEqual((lead.name, lead.user_id), ("Opp pendiente", self.salesman))
        self.assertFalse(lead.stage_id.is_won)

    def test_create_opportunity_ambiguous_partner(self):
        self.direct(self.salesman)
        res = self.sc(
            self.salesman,
            "create_opportunity",
            {"name": "Dudosa", "partner": "Duplicado"},
        )
        self.assertEqual(res["error"]["code"], "ambiguous")
        self.assertEqual(len(res["data"]["candidates"]), 2)

    def test_create_opportunity_does_not_notify(self):
        self.direct(self.salesman)
        mails = self.env["mail.mail"].search_count([])
        res = self.sc(self.salesman, "create_opportunity", {"name": "Sin avisos"})
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(self.env["mail.mail"].search_count([]), mails)
