# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestReportSaleDetails(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.config.payment_method_ids = cls.cash_pm1 | cls.bank_pm1
        tax21 = cls.taxes["tax21"]
        cls.product_rosary = cls.create_product(
            "Rosario de plata", cls.categ_basic, 12.10, tax_ids=tax21.ids
        )
        cls.product_rosary.default_code = "070047"
        cls.product_candle = cls.create_product("Vela promesa", cls.categ_basic, 0.75)
        cls.product_candle.default_code = "010001"

    def setUp(self):
        super().setUp()
        self.open_new_session()
        self.Report = self.env["report.point_of_sale.report_saledetails"]

    def _sync_orders(self, orders_params, change_by_index=None):
        """Sincroniza pedidos como lo haría el TPV.

        ``change_by_index`` indica el cambio devuelto en efectivo al pedido
        de ese índice; el servidor lo registra como un pago negativo con
        ``is_change``, igual que al cobrar desde el TPV.
        """
        order_data = [self.create_ui_order_data(**params) for params in orders_params]
        for index, change in (change_by_index or {}).items():
            order_data[index]["amount_return"] = -change
        result = self.env["pos.order"].sync_from_ui(order_data)
        return self.env["pos.order"].browse(
            [order["id"] for order in result["pos.order"]]
        )

    def _get_session_details(self):
        return self.Report.get_sale_details(session_ids=self.pos_session.ids)

    def _render_report(self, lang=None):
        report = self.env["ir.actions.report"]
        if lang:
            report = report.with_context(lang=lang)
        return report._render_qweb_html(
            "point_of_sale.sale_details_report", self.pos_session.ids
        )[0].decode()

    def _create_standard_orders(self):
        """Tres tickets: efectivo, pago mixto y efectivo con cambio."""
        return self._sync_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product_rosary, 1)],
                    "payments": [(self.cash_pm1, 12.10)],
                },
                {
                    "pos_order_lines_ui_args": [
                        (self.product_rosary, 2, 10.0),
                        (self.product_candle, 4),
                    ],
                    "payments": [(self.cash_pm1, 10.0), (self.bank_pm1, 14.78)],
                },
                {
                    "pos_order_lines_ui_args": [(self.product_candle, 2)],
                    "payments": [(self.cash_pm1, 5.0)],
                },
            ],
            change_by_index={2: 3.5},
        )

    def test_payment_methods_grouped_with_count_and_percentage(self):
        self._create_standard_orders()

        details = self._get_session_details()

        methods = {
            method["name"]: method for method in details["xtendoo_payment_methods"]
        }
        self.assertEqual(set(methods), {self.cash_pm1.name, self.bank_pm1.name})
        cash = methods[self.cash_pm1.name]
        bank = methods[self.bank_pm1.name]
        # El cambio devuelto no cuenta como cobro, pero sí descuenta importe.
        self.assertEqual(cash["count"], 3)
        self.assertAlmostEqual(cash["amount"], 12.10 + 10.0 + 5.0 - 3.5)
        self.assertEqual(bank["count"], 1)
        self.assertAlmostEqual(bank["amount"], 14.78)
        self.assertAlmostEqual(cash["percentage"] + bank["percentage"], 100.0)
        self.assertAlmostEqual(
            bank["percentage"], 14.78 * 100.0 / (23.6 + 14.78), places=4
        )
        totals = details["xtendoo_payment_totals"]
        self.assertEqual(totals["count"], 4)
        self.assertAlmostEqual(totals["amount"], 23.6 + 14.78)

    def test_payment_methods_follow_configured_sequence(self):
        self.cash_pm1.sequence = 20
        self.bank_pm1.sequence = 10
        self._create_standard_orders()

        details = self._get_session_details()

        self.assertEqual(
            [method["id"] for method in details["xtendoo_payment_methods"]],
            [self.bank_pm1.id, self.cash_pm1.id],
        )

    def test_products_one_line_per_product(self):
        self._create_standard_orders()

        details = self._get_session_details()

        products = details["xtendoo_products"]
        # El rosario se vende con y sin descuento, pero sale en una línea.
        self.assertEqual(
            [product["name"] for product in products],
            ["Rosario de plata", "Vela promesa"],
        )
        rosary, candle = products
        self.assertEqual(rosary["default_code"], "070047")
        self.assertEqual(rosary["quantity"], 3)
        self.assertAlmostEqual(rosary["total_amount"], 12.10 + 21.78)
        self.assertAlmostEqual(rosary["base_amount"], (12.10 + 21.78) / 1.21)
        self.assertEqual(candle["quantity"], 6)
        self.assertAlmostEqual(candle["base_amount"], 4.5)
        self.assertAlmostEqual(candle["total_amount"], 4.5)
        self.assertFalse(details["xtendoo_refund_products"])

    def test_summary(self):
        self._create_standard_orders()

        details = self._get_session_details()

        summary = details["xtendoo_summary"]
        self.assertAlmostEqual(summary["total"], 38.38)
        self.assertEqual(summary["order_count"], 3)
        self.assertAlmostEqual(summary["average_ticket"], 38.38 / 3)
        self.assertAlmostEqual(summary["base_amount"] + summary["tax_amount"], 38.38)
        self.assertAlmostEqual(summary["tax_amount"], 33.88 - 33.88 / 1.21)
        self.assertEqual(summary["refund_count"], 0)
        self.assertEqual(summary["refund_amount"], 0.0)

    def test_refunds(self):
        self._sync_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product_candle, 10)],
                    "payments": [(self.cash_pm1, 7.5)],
                },
                {
                    "pos_order_lines_ui_args": [(self.product_candle, -2)],
                    "pos_order_ui_args": {"is_refund": True},
                    "payments": [(self.cash_pm1, -1.5)],
                },
            ]
        )

        details = self._get_session_details()

        sales = details["xtendoo_products"]
        refunds = details["xtendoo_refund_products"]
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0]["quantity"], 10)
        self.assertEqual(len(refunds), 1)
        self.assertEqual(refunds[0]["quantity"], 2)
        self.assertAlmostEqual(refunds[0]["total_amount"], -1.5)
        summary = details["xtendoo_summary"]
        self.assertEqual(summary["refund_count"], 1)
        self.assertAlmostEqual(summary["refund_amount"], -1.5)
        self.assertAlmostEqual(summary["total"], 6.0)
        cash = details["xtendoo_payment_methods"][0]
        self.assertEqual(cash["count"], 2)
        self.assertAlmostEqual(cash["amount"], 6.0)

    def test_invoice_summary(self):
        self._sync_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product_candle, 2)],
                    "customer": self.customer,
                    "is_invoiced": True,
                },
                {
                    "pos_order_lines_ui_args": [(self.product_candle, 4)],
                    "customer": self.customer,
                    "is_invoiced": True,
                },
                {"pos_order_lines_ui_args": [(self.product_candle, 1)]},
            ]
        )
        invoices = self.pos_session.order_ids.account_move
        self.assertEqual(len(invoices), 2)

        summary = self._get_session_details()["xtendoo_invoice_summary"]

        names = sorted(invoices.mapped("name"))
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["first"], names[0])
        self.assertEqual(summary["last"], names[-1])
        self.assertAlmostEqual(summary["total"], 4.5)

    def test_empty_report(self):
        details = self._get_session_details()

        self.assertEqual(details["xtendoo_payment_methods"], [])
        self.assertEqual(details["xtendoo_payment_totals"], {"count": 0, "amount": 0})
        self.assertEqual(details["xtendoo_products"], [])
        self.assertEqual(details["xtendoo_summary"]["average_ticket"], 0.0)
        self.assertEqual(
            details["xtendoo_invoice_summary"],
            {"count": 0, "first": False, "last": False, "total": 0},
        )

    def test_report_by_dates_and_config(self):
        self._create_standard_orders()

        details = self.Report.get_sale_details(config_ids=self.config.ids)

        self.assertEqual(details["xtendoo_summary"]["order_count"], 3)
        self.assertEqual(len(details["xtendoo_products"]), 2)

    def test_rendered_report(self):
        self.product_rosary.barcode = "8400000000017"
        self._create_standard_orders()

        html = self._render_report()

        self.assertIn("Session summary", html)
        self.assertIn("Payments by method", html)
        self.assertIn("Sales by product", html)
        self.assertNotIn("/report/barcode/", html)
        self.assertEqual(html.count("Rosario de plata"), 1)
        # Los cobros se muestran antes que el detalle de productos.
        self.assertLess(
            html.index("Payments by method"), html.index("Sales by product")
        )

    def test_rendered_report_spanish_translation(self):
        self.env["res.lang"]._activate_lang("es_ES")
        self.env["ir.module.module"].search(
            [("name", "=", "xtendoo_pos_sale_details_report")]
        )._update_translations(["es_ES"])
        self._create_standard_orders()

        html = self._render_report(lang="es_ES")

        self.assertIn("Resumen de la sesión", html)
        self.assertIn("Cobros por forma de pago", html)
        self.assertIn("Ventas por producto", html)
        self.assertNotIn("Payments by method", html)
