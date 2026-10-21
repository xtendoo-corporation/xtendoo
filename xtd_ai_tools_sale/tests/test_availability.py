from odoo.tests import tagged

from .common import XtdAiSaleCase


@tagged("post_install", "-at_install")
class TestProductAvailability(XtdAiSaleCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        if "stock.quant" not in env:
            return
        cls.stocked = env["product.product"].create(
            {
                "name": "Taladro AI 800W",
                "default_code": "TAL800",
                "is_storable": True,
                "type": "consu",
                "list_price": 90.0,
            }
        )
        cls.service = env["product.product"].create(
            {"name": "Servicio AI", "type": "service", "list_price": 10.0}
        )
        cls.put_stock(cls.stocked, cls.company, 7.0)
        cls.put_stock(cls.stocked, cls.company2, 3.0)

    @classmethod
    def put_stock(cls, product, company, qty):
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )
        cls.env["stock.quant"].with_company(company)._update_available_quantity(
            product, warehouse.lot_stock_id, qty
        )

    def setUp(self):
        super().setUp()
        if "stock.quant" not in self.env:
            self.skipTest("stock is not installed")

    def test_salesman_without_inventory_rights_sees_availability(self):
        self.assertFalse(self.salesman.has_group("stock.group_stock_user"))
        self.direct(self.salesman)
        res = self.sc(self.salesman, "get_product_availability", {"product": "taladro"})
        self.assertEqual(res["status"], "ok", res)
        item = res["data"]["items"][0]
        self.assertEqual(
            (item["code"], item["on_hand"], item["free"]), ("TAL800", 7.0, 7.0)
        )
        self.assertTrue(item["stockable"])
        moves = self.env["stock.move"].with_user(self.salesman).has_access("read")
        if moves:
            self.assertEqual(item["forecasted"], 7.0)
        else:
            self.assertIsNone(item["forecasted"])
            self.assertIn("note", res["data"])
        self.assertEqual(res["records"][0]["model"], "product.product")

    def test_by_code_id_and_services(self):
        self.direct(self.salesman)
        by_code = self.sc(
            self.salesman, "get_product_availability", {"product": "TAL800"}
        )
        by_id = self.sc(
            self.salesman, "get_product_availability", {"product": str(self.stocked.id)}
        )
        self.assertEqual(
            by_code["data"]["items"][0]["id"], by_id["data"]["items"][0]["id"]
        )
        res = self.sc(
            self.salesman, "get_product_availability", {"product": "Servicio AI"}
        )
        self.assertEqual(res["status"], "error", res)
        res = self.sc(
            self.salesman, "get_product_availability", {"product": "no-existe-zzz"}
        )
        self.assertEqual(res["status"], "error", res)

    def test_multicompany_split_and_filter(self):
        self.direct(self.multi_user)
        res = self.sc(
            self.multi_user,
            "get_product_availability",
            {"product": "TAL800"},
            cids=[self.company.id, self.company2.id],
        )
        item = res["data"]["items"][0]
        by_company = {e["company"]: e["on_hand"] for e in item["by_company"]}
        self.assertEqual(by_company, {self.company.name: 7.0, self.company2.name: 3.0})
        res = self.sc(
            self.multi_user,
            "get_product_availability",
            {"product": "TAL800", "company": str(self.company2.id)},
            cids=[self.company.id, self.company2.id],
        )
        self.assertEqual(res["data"]["items"][0]["on_hand"], 3.0)

    def test_other_company_user_does_not_see_foreign_stock(self):
        self.direct(self.other_company_user)
        res = self.sc(
            self.other_company_user,
            "get_product_availability",
            {"product": "TAL800"},
            cids=[self.company2.id],
        )
        self.assertEqual(res["data"]["items"][0]["on_hand"], 3.0)

    def test_visibility_by_group(self):
        run, _t = self.start_run(self.salesman)
        _s, response = self.rpc(self.salesman, run, "tools/list", {})
        names = {t["name"] for t in response["result"]["tools"]}
        self.assertIn("get_product_availability", names)
        run, _t = self.start_run(self.nosales)
        _s, response = self.rpc(self.nosales, run, "tools/list", {})
        names = {t["name"] for t in response["result"]["tools"]}
        self.assertNotIn("get_product_availability", names)
        status, response = self.rpc(
            self.nosales,
            run,
            "tools/call",
            {"name": "get_product_availability", "arguments": {"product": "TAL800"}},
        )
        self.assertEqual(response["error"]["code"], -32601)

    def test_sales_report_description_points_to_search(self):
        tool = self.env["xtd.ai.toolbox"]._xtd_ai_tools()["sales_report"]
        for word in ("search_sale_orders", "total_orders", "NO lista documentos"):
            self.assertIn(word, tool["description"])
