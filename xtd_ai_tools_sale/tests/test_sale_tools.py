from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import INJECTION, XtdAiSaleCase

SALE_TOOLS = {
    "search_sale_orders",
    "get_sale_order",
    "sales_report",
    "create_sale_quotation",
    "add_sale_order_lines",
    "search_opportunities",
    "get_opportunity",
    "pipeline_report",
    "create_opportunity",
}


@tagged("post_install", "-at_install")
class TestSaleTools(XtdAiSaleCase):
    # -- visibility and permissions -----------------------------------------
    def tool_names(self, user, cids=None):
        run, _t = self.start_run(user)
        status, response = self.rpc(user, run, "tools/list", {}, cids=cids)
        self.assertEqual(status, 200, response)
        return {t["name"] for t in response["result"]["tools"]}

    def test_tools_list_by_group(self):
        for user in (self.salesman, self.sales_manager, self.multi_user):
            self.assertTrue(SALE_TOOLS <= self.tool_names(user), user.login)
        self.assertFalse(SALE_TOOLS & self.tool_names(self.nosales))

    def test_tool_schemas_and_kinds(self):
        run, _t = self.start_run(self.salesman)
        _status, response = self.rpc(self.salesman, run, "tools/list", {})
        tools = {t["name"]: t for t in response["result"]["tools"]}
        kinds = {n: tools[n]["annotations"]["xtdKind"] for n in SALE_TOOLS}
        self.assertEqual(
            {n for n, k in kinds.items() if k == "draft"},
            {"create_sale_quotation", "add_sale_order_lines", "create_opportunity"},
        )
        for name in SALE_TOOLS:
            schema = tools[name]["inputSchema"]
            self.assertIs(schema["additionalProperties"], False, name)
            self.assertIn("required", schema, name)

    def test_non_sales_user_forced_call_is_denied(self):
        run, _t = self.start_run(self.nosales)
        for name, args in (("search_sale_orders", {}), ("pipeline_report", {})):
            status, response = self.rpc(
                self.nosales, run, "tools/call", {"name": name, "arguments": args}
            )
            self.assertEqual(response["error"]["code"], -32601, name)
        # even bypassing the visibility filter the ORM refuses
        env = self.tool_env(self.nosales, run)
        toolbox = env["xtd.ai.toolbox"]
        for name, args in (
            ("search_sale_orders", {}),
            ("search_opportunities", {}),
            (
                "sales_report",
                {
                    "group_by": "customer",
                    "date_from": "2020-01-01",
                    "date_to": "2030-01-01",
                },
            ),
        ):
            tool = toolbox._xtd_ai_tools()[name]
            with self.assertRaises(AccessError, msg=name):
                toolbox._xtd_ai_execute(tool, args)
        result = env["xtd.ai.mcp"]._xtd_ai_error_result(AccessError("x"))
        self.assertEqual(result[0]["error"]["code"], "access_denied")

    def test_read_respects_own_documents_rule(self):
        mine = self.make_order(user=self.salesman)
        theirs = self.make_order(user=self.salesman2)
        res = self.sc(self.salesman, "search_sale_orders")
        names = {r["name"] for r in res["data"]["items"]}
        self.assertEqual(res["status"], "ok")
        self.assertIn(mine.name, names)
        self.assertNotIn(theirs.name, names)
        res = self.sc(self.sales_manager, "search_sale_orders")
        names = {r["name"] for r in res["data"]["items"]}
        self.assertLessEqual({mine.name, theirs.name}, names)
        # get_sale_order of somebody else's order: not visible
        res = self.sc(self.salesman, "get_sale_order", {"order": theirs.name})
        self.assertEqual(res["error"]["code"], "not_found")
        res = self.sc(self.salesman, "get_sale_order", {"order": str(theirs.id)})
        self.assertEqual(res["error"]["code"], "not_found")

    def test_read_respects_multicompany(self):
        o1 = self.make_order(user=self.multi_user)
        o2 = self.make_order(user=self.multi_user, company=self.company2)
        res = self.sc(self.multi_user, "search_sale_orders", cids=[self.company.id])
        names = {r["name"] for r in res["data"]["items"]}
        self.assertIn(o1.name, names)
        self.assertNotIn(o2.name, names)
        res = self.sc(
            self.multi_user,
            "search_sale_orders",
            cids=[self.company2.id, self.company.id],
        )
        names = {r["name"] for r in res["data"]["items"]}
        self.assertLessEqual({o1.name, o2.name}, names)
        # a user that only belongs to the other company never sees company 1 documents
        res = self.sc(
            self.other_company_user, "search_sale_orders", cids=[self.company2.id]
        )
        names = {r["name"] for r in res["data"]["items"]}
        self.assertNotIn(o1.name, names)
        res = self.sc(
            self.other_company_user,
            "get_sale_order",
            {"order": o1.name},
            cids=[self.company2.id],
        )
        self.assertEqual(res["error"]["code"], "not_found")

    # -- search --------------------------------------------------------------
    def test_search_filters(self):
        quote = self.make_order(partner=self.partner, lines=[(self.product, 1.0)])
        order = self.make_order(partner=self.partner_b, lines=[(self.product, 10.0)])
        order.action_confirm()
        sent = self.make_order(partner=self.partner, lines=[(self.product2, 1.0)])
        sent.state = "sent"

        def search(**args):
            res = self.sc(self.salesman, "search_sale_orders", args)
            self.assertEqual(res["status"], "ok", res)
            return {r["name"]: r for r in res["data"]["items"]}

        self.assertIn(quote.name, search(kind="quotation"))
        self.assertIn(sent.name, search(kind="quotation"))
        self.assertNotIn(order.name, search(kind="quotation"))
        self.assertEqual(
            set(search(kind="order")) & {quote.name, order.name, sent.name},
            {order.name},
        )
        self.assertEqual(
            set(search(state="sent")) & {quote.name, sent.name}, {sent.name}
        )
        self.assertEqual(set(search(partner="Cliente Beta")), {order.name})
        self.assertEqual(
            set(search(partner=str(self.partner.id))) & {quote.name, order.name},
            {quote.name},
        )
        self.assertEqual(set(search(min_amount=900)), {order.name})
        self.assertEqual(set(search(max_amount=60)), {sent.name})
        today = str(fields.Date.today())
        self.assertIn(order.name, search(date_from=today, date_to=today))
        self.assertFalse(search(date_from="2000-01-01", date_to="2000-12-31"))
        self.assertIn(order.name, search(salesperson=self.salesman.name))
        row = search(partner="Cliente Beta")[order.name]
        self.assertEqual(
            row["amount_untaxed"],
            {"amount": 1000.0, "currency": order.currency_id.name},
        )
        self.assertEqual(row["kind"], "order")
        res = self.sc(self.salesman, "search_sale_orders", {"partner": "Cliente"})
        self.assertEqual(res["error"]["code"], "ambiguous")
        self.assertTrue(res["data"]["candidates"])
        res = self.sc(
            self.salesman,
            "search_sale_orders",
            {"date_from": "2026-02-01", "date_to": "2026-01-01"},
        )
        self.assertEqual(res["error"]["code"], "validation")

    def test_search_limit_truncates(self):
        for _i in range(3):
            self.make_order()
        res = self.sc(self.salesman, "search_sale_orders", {"limit": 2})
        self.assertEqual(len(res["data"]["items"]), 2)
        self.assertTrue(res["data"]["truncated"])
        self.assertGreaterEqual(res["data"]["total"], 3)

    def test_get_sale_order_detail_and_injection(self):
        order = self.make_order(
            lines=[(self.product, 3.0)], note=INJECTION, client_order_ref=INJECTION
        )
        order.order_line[0].name = INJECTION * 8
        res = self.sc(self.salesman, "get_sale_order", {"order": order.name})
        self.assertEqual(res["status"], "ok", res)
        data = res["data"]
        self.assertEqual(data["name"], order.name)
        self.assertEqual(data["notes"]["untrusted_text"], INJECTION)
        self.assertEqual(data["customer_reference"]["untrusted_text"], INJECTION)
        line = data["lines"][0]
        self.assertTrue(line["name"]["truncated"])
        self.assertLessEqual(len(line["name"]["untrusted_text"]), 300)
        self.assertEqual(line["quantity"], 3.0)
        self.assertEqual(line["subtotal"]["amount"], 300.0)
        self.assertEqual(res["records"][0]["model"], "sale.order")
        self.assertNotIn("email", str(data["partner"]))

    def test_partner_name_injection_is_untrusted(self):
        evil = self.env["res.partner"].create({"name": INJECTION})
        self.make_order(partner=evil)
        res = self.sc(self.salesman, "search_sale_orders", {"partner": str(evil.id)})
        partner = res["data"]["items"][0]["partner"]
        self.assertEqual(partner["name"]["untrusted_text"], INJECTION)

    # -- report --------------------------------------------------------------
    def test_sales_report(self):
        today = str(fields.Date.today())
        o1 = self.make_order(
            partner=self.partner, lines=[(self.product, 2.0), (self.product2, 4.0)]
        )
        o2 = self.make_order(partner=self.partner_b, lines=[(self.product, 1.0)])
        o3 = self.make_order(
            partner=self.partner_b, lines=[(self.product, 100.0)], user=self.salesman2
        )
        quote = self.make_order(partner=self.partner, lines=[(self.product, 7.0)])
        (o1 | o2 | o3).action_confirm()
        self.env.flush_all()
        args = {"date_from": today, "date_to": today}

        def report(user, group_by, **extra):
            res = self.sc(user, "sales_report", args | {"group_by": group_by} | extra)
            self.assertEqual(res["status"], "ok", res)
            return res["data"]

        data = report(self.salesman, "customer")
        by_customer = {
            r["customer"]["name"]["untrusted_text"]: r for r in data["items"]
        }
        self.assertEqual(
            by_customer["Cliente Alfa SL"]["amount_untaxed"]["amount"], 400.0
        )
        self.assertEqual(
            by_customer["Cliente Beta SL"]["amount_untaxed"]["amount"], 100.0
        )
        self.assertEqual(
            data["total_amount_untaxed"]["amount"], 500.0
        )  # own documents only
        data = report(self.sales_manager, "customer")
        by_customer = {
            r["customer"]["name"]["untrusted_text"]: r
            for r in data["items"]
            if r["customer"]
        }
        self.assertEqual(
            by_customer["Cliente Beta SL"]["amount_untaxed"]["amount"], 10100.0
        )
        self.assertEqual(
            by_customer["Cliente Alfa SL"]["amount_untaxed"]["amount"], 400.0
        )
        data = report(self.salesman, "customer", include_quotations=True)
        self.assertEqual(data["total_amount_untaxed"]["amount"], 1200.0)
        self.assertIn(quote.partner_id.id, [r["customer"]["id"] for r in data["items"]])
        data = report(self.sales_manager, "product")
        by_product = {r["product"]["id"]: r for r in data["items"]}
        self.assertEqual(by_product[self.product.id]["quantity"], 103.0)
        self.assertEqual(by_product[self.product2.id]["quantity"], 4.0)
        data = report(self.sales_manager, "salesperson")
        by_user = {r["salesperson"]["id"]: r for r in data["items"]}
        self.assertEqual(
            by_user[self.salesman2.id]["amount_untaxed"]["amount"], 10000.0
        )
        data = report(self.salesman, "month")
        self.assertEqual(data["items"][0]["month"], today[:7])
        self.assertEqual(data["items"][0]["amount_untaxed"]["amount"], 500.0)
        # one month row, but two orders (o1 has 2 lines, o2 has 1): never confuse them
        self.assertEqual(data["items"][0]["orders"], 2)
        self.assertEqual(data["items"][0]["lines"], 3)
        self.assertEqual(data["total_orders"], 2)
        data = report(self.salesman, "customer", limit=1)
        self.assertEqual(len(data["items"]), 1)
        self.assertTrue(data["truncated"])
        # out of range
        res = self.sc(
            self.salesman,
            "sales_report",
            {
                "group_by": "customer",
                "date_from": "2000-01-01",
                "date_to": "2000-12-31",
            },
        )
        self.assertEqual(res["data"]["items"], [])
        self.assertEqual(res["data"]["total_amount_untaxed"]["amount"], 0.0)

    def test_sales_report_multicompany(self):
        today = str(fields.Date.today())
        o1 = self.make_order(user=self.multi_user, lines=[(self.product, 1.0)])
        o2 = self.make_order(
            user=self.multi_user, lines=[(self.product, 5.0)], company=self.company2
        )
        (o1 | o2).action_confirm()
        self.env.flush_all()
        args = {"group_by": "customer", "date_from": today, "date_to": today}
        res = self.sc(self.multi_user, "sales_report", args, cids=[self.company.id])
        self.assertEqual(res["data"]["total_amount_untaxed"]["amount"], 100.0)
        res = self.sc(
            self.other_company_user, "sales_report", args, cids=[self.company2.id]
        )
        self.assertEqual(
            res["data"]["total_amount_untaxed"]["amount"], 0.0
        )  # not their documents

    # -- drafts --------------------------------------------------------------
    def quotation_args(self, **extra):
        return {
            "partner": str(self.partner.id),
            "lines": [
                {"product": str(self.product.id), "quantity": 3},
                {
                    "product": "Gadget XT",
                    "quantity": 2,
                    "price_unit": 40.0,
                    "discount": 10,
                },
            ],
        } | extra

    def test_create_quotation_direct(self):
        self.direct(self.salesman)
        res = self.sc(
            self.salesman,
            "create_sale_quotation",
            self.quotation_args(client_order_ref="PO-77", validity_date="2030-01-31"),
        )
        self.assertEqual(res["status"], "ok", res)
        order = self.env["sale.order"].browse(res["records"][0]["id"])
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.partner_id, self.partner)
        self.assertEqual(order.user_id, self.salesman)
        self.assertEqual(order.create_uid, self.salesman)
        self.assertEqual(len(order.order_line), 2)
        self.assertEqual(order.client_order_ref, "PO-77")
        self.assertEqual(str(order.validity_date), "2030-01-31")
        line1, line2 = order.order_line
        self.assertEqual(line1.price_unit, 100.0)  # computed by Odoo (list price)
        self.assertEqual((line2.price_unit, line2.discount), (40.0, 10.0))
        self.assertEqual(order.amount_untaxed, 300.0 + 72.0)
        self.assertEqual(res["data"]["state"], "draft")
        self.assertEqual(res["data"]["lines_count"], 2)

    def test_create_quotation_pending_confirmation_flow(self):
        self.set_confirm(self.salesman, True)
        before = self.env["sale.order"].search_count([])
        run, _t = self.start_run(self.salesman)
        res = self.sc(
            self.salesman, "create_sale_quotation", self.quotation_args(), run=run
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertIn("Cliente Alfa SL", res["summary"])
        self.assertIn("2 líneas", res["summary"])
        self.assertIn("372", res["summary"])
        self.assertEqual(self.env["sale.order"].search_count([]), before)
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.salesman)
            .browse(res["pending_action_id"])
        )
        self.assertEqual(action.preview["lines"][1]["subtotal"]["amount"], 72.0)
        result = action.action_confirm()
        self.assertEqual(result["state"], "confirmed", result)
        order = self.env["sale.order"].browse(action.result_res_id)
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.create_uid, self.salesman)
        self.assertEqual(self.env["sale.order"].search_count([]), before + 1)

    def test_preview_does_not_consume_sequence_or_create(self):
        self.set_confirm(self.salesman, True)
        before = self.env["sale.order"].search_count([])
        self.sc(self.salesman, "create_sale_quotation", self.quotation_args())
        self.assertEqual(self.env["sale.order"].search_count([]), before)

    def test_create_quotation_resolution_errors(self):
        self.direct(self.salesman)
        res = self.sc(
            self.salesman,
            "create_sale_quotation",
            self.quotation_args(partner="Duplicado"),
        )
        self.assertEqual(res["error"]["code"], "ambiguous")
        self.assertEqual(len(res["data"]["candidates"]), 2)
        args = self.quotation_args()
        args["lines"][0]["product"] = "Tornillo"
        res = self.sc(self.salesman, "create_sale_quotation", args)
        self.assertEqual(res["error"]["code"], "ambiguous")
        args["lines"][0]["product"] = "Producto inexistente zzz"
        self.assertEqual(
            self.sc(self.salesman, "create_sale_quotation", args)["error"]["code"],
            "not_found",
        )
        args["lines"][0]["product"] = "Interno XT"  # not sellable
        self.assertEqual(
            self.sc(self.salesman, "create_sale_quotation", args)["error"]["code"],
            "not_found",
        )
        self.assertEqual(
            self.sc(
                self.salesman,
                "create_sale_quotation",
                self.quotation_args(partner="nadie zzz"),
            )["error"]["code"],
            "not_found",
        )

    def test_create_quotation_argument_validation(self):
        self.direct(self.salesman)
        for args in (
            {"partner": "1"},  # no lines
            self.quotation_args() | {"lines": []},
            self.quotation_args()
            | {"state": "sale"},  # unknown property: never accept states
            self.quotation_args() | {"user_id": 1},
            self.quotation_args()
            | {"lines": [{"product": "1", "quantity": 1, "state": "x"}]},
            self.quotation_args() | {"lines": [{"product": "1"}]},  # missing quantity
            self.quotation_args() | {"validity_date": "31/01/2030"},
        ):
            res = self.sc(self.salesman, "create_sale_quotation", args)
            self.assertEqual(res["error"]["code"], "validation", args)
        res = self.sc(
            self.salesman,
            "create_sale_quotation",
            self.quotation_args()
            | {"lines": [{"product": str(self.product.id), "quantity": 0}]},
        )
        self.assertEqual(res["error"]["code"], "validation")

    def test_create_quotation_is_always_draft_even_with_tampered_create(self):
        """A create override that confirms the order is blocked and rolled back."""
        self.direct(self.salesman)
        model_cls = type(self.env["sale.order"])
        original = model_cls.create

        def evil_create(self_, vals_list):
            orders = original(self_, vals_list)
            orders.action_confirm()  # what an automated action could do
            return orders

        before = self.env["sale.order"].search_count([])
        run, _t = self.start_run(self.salesman)
        model_cls.create = evil_create
        try:
            res = self.sc(
                self.salesman, "create_sale_quotation", self.quotation_args(), run=run
            )
        finally:
            model_cls.create = original
        self.assertEqual(res["error"]["code"], "draft_only", res)
        self.assertEqual(self.env["sale.order"].search_count([]), before)
        self.assertEqual(
            self.audits(run, event="guard_blocked").mapped("outcome"), ["denied"]
        )

    def test_state_check_after_create(self):
        """If something leaves the new order out of draft the tool aborts."""
        self.direct(self.salesman)
        model_cls = type(self.env["sale.order"])
        original = model_cls.create

        def create_sent(self_, vals_list):
            orders = original(self_, vals_list)
            orders.state = "sent"
            return orders

        model_cls.create = create_sent
        try:
            res = self.sc(self.salesman, "create_sale_quotation", self.quotation_args())
        finally:
            model_cls.create = original
        self.assertEqual(res["error"]["code"], "draft_only", res)

    def test_add_lines_to_draft_order(self):
        self.direct(self.salesman)
        order = self.make_order(lines=[(self.product, 1.0)])
        res = self.sc(
            self.salesman,
            "add_sale_order_lines",
            {
                "order": order.name,
                "lines": [
                    {"product": "WXT", "quantity": 2},
                    {"product": "Gadget XT", "quantity": 1},
                ],
            },
        )
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(len(order.order_line), 3)
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.amount_untaxed, 100 + 200 + 50)
        self.assertEqual(res["data"]["lines_added"], 2)
        added = res["data"]["added_lines"]
        self.assertEqual(len(added), 2)
        self.assertEqual(
            {a["id"] for a in added}, set((order.order_line - order.order_line[:1]).ids)
        )
        self.assertEqual(sorted(a["quantity"] for a in added), [1.0, 2.0])
        self.assertTrue(
            all(
                {"product", "price_unit", "discount", "subtotal"} <= set(a)
                for a in added
            )
        )
        self.assertEqual(res["data"]["amount_untaxed"]["amount"], 350.0)
        self.assertIn("amount_total", res["data"])
        self.assertEqual(res["records"][0]["name"], order.name)

    def test_add_lines_preview_and_pending(self):
        self.set_confirm(self.salesman, True)
        order = self.make_order(lines=[(self.product, 1.0)])
        res = self.sc(
            self.salesman,
            "add_sale_order_lines",
            {"order": order.name, "lines": [{"product": "WXT", "quantity": 2}]},
        )
        self.assertEqual(res["status"], "pending_confirmation", res)
        self.assertIn(order.name, res["summary"])
        self.assertIn("200", res["summary"])
        self.assertEqual(len(order.order_line), 1)
        action = (
            self.env["xtd.ai.pending_action"]
            .with_user(self.salesman)
            .browse(res["pending_action_id"])
        )
        self.assertEqual(action.action_confirm()["state"], "confirmed")
        self.assertEqual(len(order.order_line), 2)

    def test_add_lines_refuses_non_draft(self):
        self.direct(self.salesman)
        sent = self.make_order()
        sent.state = "sent"
        confirmed = self.make_order()
        confirmed.action_confirm()
        cancelled = self.make_order()
        cancelled.action_cancel()
        for order in (sent, confirmed, cancelled):
            res = self.sc(
                self.salesman,
                "add_sale_order_lines",
                {"order": order.name, "lines": [{"product": "WXT", "quantity": 1}]},
            )
            self.assertEqual(res["error"]["code"], "validation", (order.state, res))
            self.assertEqual(len(order.order_line), 1)
        # also at preview time (confirmation on)
        self.set_confirm(self.salesman, True)
        res = self.sc(
            self.salesman,
            "add_sale_order_lines",
            {"order": confirmed.name, "lines": [{"product": "WXT", "quantity": 1}]},
        )
        self.assertEqual(res["error"]["code"], "validation")

    def test_add_lines_other_users_order_not_found(self):
        self.direct(self.salesman)
        theirs = self.make_order(user=self.salesman2)
        res = self.sc(
            self.salesman,
            "add_sale_order_lines",
            {"order": str(theirs.id), "lines": [{"product": "WXT", "quantity": 1}]},
        )
        self.assertEqual(res["error"]["code"], "not_found")
        self.assertEqual(len(theirs.order_line), 1)

    def test_non_sales_user_cannot_create(self):
        self.direct(self.nosales)
        run, _t = self.start_run(self.nosales)
        status, response = self.rpc(
            self.nosales,
            run,
            "tools/call",
            {"name": "create_sale_quotation", "arguments": self.quotation_args()},
        )
        self.assertEqual(response["error"]["code"], -32601)
        self.assertEqual(
            self.env["sale.order"].search_count([("create_uid", "=", self.nosales.id)]),
            0,
        )

    def test_create_does_not_send_mail(self):
        self.direct(self.salesman)
        mails = self.env["mail.mail"].search_count([])
        res = self.sc(self.salesman, "create_sale_quotation", self.quotation_args())
        self.assertEqual(res["status"], "ok", res)
        self.assertEqual(self.env["mail.mail"].search_count([]), mails)
        self.assertTrue(Command)  # keep import used
