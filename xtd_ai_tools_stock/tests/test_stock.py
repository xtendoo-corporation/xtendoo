from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.xtd_ai.tests.common import AI_GROUPS, XtdAiCase
from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError

STOCK_TOOLS = {
    "get_stock_levels",
    "search_pickings",
    "get_picking",
    "stock_move_history",
}


@tagged("post_install", "-at_install")
class TestStock(XtdAiCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.keeper = new_test_user(
            cls.env, "xtd_ai_keeper", groups=AI_GROUPS + ",stock.group_stock_user"
        )
        cls.nobody = new_test_user(cls.env, "xtd_ai_nobody", groups=AI_GROUPS)
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Proveedor Zeta SL", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Tornillo Zeta",
                "default_code": "TZ-1",
                "type": "consu",
                "is_storable": True,
                "list_price": 1.0,
                "standard_price": 0.5,
            }
        )

    # ------------------------------------------------------------------
    def run_for(self, user):
        """One run per user and test (the gateway allows a single active run)."""
        runs = self.__dict__.setdefault("_runs", {})
        if user.id not in runs:
            runs[user.id] = self.start_run(user)[0]
        return runs[user.id]

    def tool(self, user, name, args=None, **kw):
        run = self.run_for(user)
        return self.call(user, run, name, args or {}, **kw)["structuredContent"]

    def listed(self, user):
        run = self.run_for(user)
        status, response = self.rpc(user, run, "tools/list", {})
        self.assertEqual(status, 200)
        return {t["name"] for t in response["result"]["tools"]}

    # ------------------------------------------------------------------
    # Permission matrix
    # ------------------------------------------------------------------
    def test_visibility_matrix(self):
        self.assertEqual(self.listed(self.keeper) & STOCK_TOOLS, STOCK_TOOLS)
        self.assertEqual(self.listed(self.nobody) & STOCK_TOOLS, set())

    def test_forced_call_of_hidden_tool(self):
        run = self.run_for(self.nobody)
        status, response = self.rpc(
            self.nobody, run, "tools/call", {"name": "search_pickings", "arguments": {}}
        )
        self.assertEqual(response["error"]["code"], -32601)

    def test_tool_bodies_check_group_when_forced(self):
        tools = self.env["xtd.ai.toolbox"]._xtd_ai_tools()
        for name, args in (
            ("get_stock_levels", {"products": ["TZ-1"]}),
            ("search_pickings", {}),
        ):
            run = self.run_for(self.nobody)
            env = self.tool_env(self.nobody, run)
            with self.assertRaises(AccessError, msg=name):
                env["xtd.ai.toolbox"]._xtd_ai_execute(tools[name], args)

    def make_picking(self, code="incoming", warehouse=None, qty=4.0):
        warehouse = warehouse or self.warehouse1
        picking_type = (
            warehouse.in_type_id if code == "incoming" else warehouse.out_type_id
        )
        src = (
            self.env.ref("stock.stock_location_suppliers")
            if code == "incoming"
            else warehouse.lot_stock_id
        )
        dst = (
            warehouse.lot_stock_id
            if code == "incoming"
            else self.env.ref("stock.stock_location_customers")
        )
        return self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "partner_id": self.vendor.id,
                "origin": "TEST-ORIGIN",
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "product_uom": self.product.uom_id.id,
                            "location_id": src.id,
                            "location_dest_id": dst.id,
                        }
                    )
                ],
            }
        )

    def _prepare_stock(self):
        self.warehouse1 = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        self.warehouse2 = self.env["stock.warehouse"].create(
            {"name": "Almacen Norte Zeta", "code": "ZN2", "company_id": self.company.id}
        )
        quant = self.env["stock.quant"]
        quant._update_available_quantity(
            self.product, self.warehouse1.lot_stock_id, 10.0
        )
        quant._update_available_quantity(
            self.product, self.warehouse2.lot_stock_id, 5.0
        )

    def test_stock_picking_guards(self):
        self._prepare_stock()
        picking = self.make_picking("outgoing", qty=2)
        run = self.run_for(self.keeper)
        agent_picking = self.tool_env(self.keeper, run)["stock.picking"].browse(
            picking.id
        )
        for method in (
            "action_confirm",
            "action_assign",
            "button_validate",
            "_action_done",
            "unlink",
        ):
            with self.assertRaises(XtdAiDraftOnlyError, msg=method):
                getattr(agent_picking, method)()
        self.assertEqual(picking.state, "draft")
        # normal behaviour without xtd_ai_run
        picking.with_user(self.keeper).action_confirm()
        picking.with_user(self.keeper).action_assign()
        self.assertEqual(picking.state, "assigned")
        picking.with_user(self.keeper).action_cancel()
        picking.unlink()
        self.assertFalse(picking.exists())

    # ------------------------------------------------------------------
    # Stock read tools
    # ------------------------------------------------------------------
    def test_stock_levels_two_warehouses(self):
        self._prepare_stock()
        delivery = self.make_picking("outgoing", warehouse=self.warehouse1, qty=3)
        delivery.action_confirm()
        delivery.action_assign()
        receipt = self.make_picking("incoming", warehouse=self.warehouse2, qty=6)
        receipt.action_confirm()
        self.env.flush_all()
        res = self.tool(self.keeper, "get_stock_levels", {"products": ["TZ-1"]})
        self.assertEqual(res["status"], "ok", res)
        row = res["data"]["items"][0]
        by_wh = {w["warehouse"]["id"]: w for w in row["warehouses"]}
        w1, w2 = by_wh[self.warehouse1.id], by_wh[self.warehouse2.id]
        self.assertEqual(
            (w1["on_hand"], w1["reserved"], w1["available"], w1["forecasted"]),
            (10, 3, 7, 7),
        )
        self.assertEqual(
            (w2["on_hand"], w2["reserved"], w2["available"], w2["forecasted"]),
            (5, 0, 5, 11),
        )
        total = row["total"]
        self.assertEqual(
            (
                total["on_hand"],
                total["reserved"],
                total["available"],
                total["forecasted"],
            ),
            (15, 3, 12, 18),
        )
        one = self.tool(
            self.keeper,
            "get_stock_levels",
            {"products": ["Tornillo Zeta"], "warehouse": "ZN2"},
        )
        item = one["data"]["items"][0]
        self.assertEqual(len(item["warehouses"]), 1)
        self.assertNotIn("total", item)
        self.assertEqual(item["warehouses"][0]["on_hand"], 5)
        self.assertEqual(item["warehouses"][0]["forecasted"], 11)

    def test_stock_levels_ambiguous_and_missing(self):
        self.env["product.product"].create(
            {"name": "Cable Zeta A", "default_code": "CZ-A"}
        )
        self.env["product.product"].create(
            {"name": "Cable Zeta B", "default_code": "CZ-B"}
        )
        res = self.tool(self.keeper, "get_stock_levels", {"products": ["Cable Zeta"]})
        self.assertEqual(res["error"]["code"], "ambiguous")
        res = self.tool(self.keeper, "get_stock_levels", {"products": ["Nada de nada"]})
        self.assertEqual(res["error"]["code"], "not_found")

    def test_pickings_and_history(self):
        self._prepare_stock()
        receipt = self.make_picking("incoming", warehouse=self.warehouse1, qty=4)
        receipt.action_confirm()
        receipt.move_ids.quantity = 4
        receipt.move_ids.picked = True
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")
        delivery = self.make_picking("outgoing", warehouse=self.warehouse1, qty=2)
        delivery.action_confirm()
        self.env.flush_all()
        res = self.tool(
            self.keeper,
            "search_pickings",
            {"type": "receipt", "state": "done", "origin": "TEST-ORIGIN"},
        )
        self.assertEqual([r["id"] for r in res["data"]["items"]], [receipt.id])
        res = self.tool(
            self.keeper, "search_pickings", {"type": "delivery", "origin": "test-orig"}
        )
        self.assertEqual([r["id"] for r in res["data"]["items"]], [delivery.id])
        res = self.tool(
            self.keeper,
            "search_pickings",
            {"partner": "Proveedor Zeta", "origin": "TEST-ORIGIN"},
        )
        self.assertEqual(res["data"]["total"], 2)
        res = self.tool(self.keeper, "get_picking", {"name": receipt.name})
        self.assertEqual(res["status"], "ok", res)
        move = res["data"]["moves"]["items"][0]
        self.assertEqual(
            (move["demand"], move["quantity"], move["state"]), (4, 4, "done")
        )
        self.assertEqual(res["data"]["type"], "receipt")
        self.assertEqual(set(res["data"]["origin"]), {"untrusted_text", "truncated"})
        res = self.tool(self.keeper, "stock_move_history", {"product": "TZ-1"})
        self.assertEqual(res["status"], "ok", res)
        items = res["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["direction"], items[0]["quantity"]), ("in", 4))
        self.assertEqual(items[0]["picking"]["id"], receipt.id)
        res = self.tool(
            self.keeper, "stock_move_history", {"product": "TZ-1", "direction": "out"}
        )
        self.assertEqual(res["data"]["total"], 0)
