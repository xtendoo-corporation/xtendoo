# -*- coding: utf-8 -*-

import inspect
import unittest
from datetime import timedelta

from odoo import fields
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


class TestXtdDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref("base.user_admin").sudo()

    def test_default_dashboard_blocks_are_available(self):
        blocks = self.env["xtd.dashboard.block"].with_context(active_test=False).search([])

        self.assertTrue(blocks)
        self.assertIn("main_kpis", blocks.mapped("technical_key"))
        self.assertIn("kpi_sales", blocks.mapped("technical_key"))
        self.assertIn("kpi_orders", blocks.mapped("technical_key"))
        self.assertIn("kpi_purchase_orders", blocks.mapped("technical_key"))
        self.assertIn("kpi_invoiced", blocks.mapped("technical_key"))
        self.assertIn("sales_chart", blocks.mapped("technical_key"))
        self.assertIn("pending_activities", blocks.mapped("technical_key"))
        self.assertIn("top_products", blocks.mapped("technical_key"))
        self.assertIn("order_status", blocks.mapped("technical_key"))
        self.assertFalse(blocks.filtered(lambda block: block.technical_key == "main_kpis").active)
        self.assertTrue(blocks.filtered(lambda block: block.technical_key == "kpi_sales").active)
        self.assertFalse(blocks.filtered(lambda block: block.technical_key == "sale_recent_quotes").active)

    def test_dashboard_service_returns_global_layout_by_default(self):
        layout = self.env["xtd.dashboard.service"].get_dashboard_layout()

        self.assertEqual(layout["mode"], "global")
        self.assertTrue(layout["blocks"])
        self.assertEqual(layout["blocks"][0]["component"], "single_kpi")
        self.assertEqual(layout["blocks"][0]["config"]["kpi_key"], "sales")
        self.assertNotIn("main_kpis", [block["key"] for block in layout["blocks"]])
        self.assertNotIn("sale_recent_quotes", [block["key"] for block in layout["blocks"]])

    def test_user_custom_dashboard_flag_is_stored_in_user_settings(self):
        self.admin.xtd_use_custom_dashboard = True

        self.assertTrue(self.admin.res_users_settings_id.xtd_use_custom_dashboard)
        self.assertTrue(self.admin.xtd_use_custom_dashboard)

    def test_dashboard_service_saves_global_layout_for_admin(self):
        service = self.env["xtd.dashboard.service"]
        layout = service.get_dashboard_layout()
        blocks = list(reversed(layout["blocks"]))

        updated_layout = service.save_dashboard_layout(blocks)

        self.assertEqual(
            [block["block_id"] for block in updated_layout["blocks"]],
            [block["block_id"] for block in blocks],
        )

    def test_dashboard_service_keeps_hidden_flag_when_saving(self):
        service = self.env["xtd.dashboard.service"]
        blocks = service.get_dashboard_layout()["blocks"]
        blocks[0]["config"] = {**blocks[0]["config"], "hidden": True}

        updated_layout = service.save_dashboard_layout(blocks)

        self.assertTrue(updated_layout["blocks"][0]["config"]["hidden"])
        self.assertFalse(updated_layout["blocks"][1]["config"].get("hidden"))

    def test_dashboard_service_deletes_custom_block(self):
        block = self.env["xtd.dashboard.block"].create({
            "name": "Contactos",
            "technical_key": "custom_res_partner_test",
            "block_type": "list",
            "component": "generic_list",
            "model_name": "res.partner",
            "config": {"fields": ["display_name"]},
        })
        self.env["xtd.dashboard.layout"].create({"block_id": block.id})
        service = self.env["xtd.dashboard.service"]
        self.assertIn(block.id, [b["block_id"] for b in service.get_dashboard_layout()["blocks"]])

        layout = service.delete_custom_block(block.id)

        self.assertNotIn(block.id, [b["block_id"] for b in layout["blocks"]])
        self.assertFalse(block.exists())


# sale no es dependencia del módulo: estos tests necesitan el registro completo.
@tagged("post_install", "-at_install")
class TestXtdDashboardSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "sale.order" not in cls.env:
            raise unittest.SkipTest("Se necesita el módulo sale")
        cls.company_1 = cls.env.company
        # Datos propios: el test no depende de lo que haya en la base de datos.
        cls.company_2 = cls.env["res.company"].create({"name": "Xtd Test Company 2"})
        cls.admin = cls.env.ref("base.user_admin")
        cls.admin.company_ids |= cls.company_2
        cls.admin.tz = "UTC"
        # Un cliente sin empresa asignada vale para pedidos de cualquier empresa.
        cls.partner = cls.env["res.partner"].create({"name": "Xtd Test Customer", "company_id": False})
        cls.product = cls.env["product.product"].create({
            "name": "Xtd Test Product",
            "type": "consu",
            "list_price": 1.0,
            "company_id": False,
        })
        cls.service = cls.env["xtd.dashboard.service"]

    def _make_order(self, company, amount, currency=None, state="sale", qty=1, product=None):
        line = {
            "name": "Servicio",
            "product_uom_qty": qty,
            "price_unit": amount,
            "tax_ids": [(5, 0, 0)],
        }
        if product:
            line["product_id"] = product.id
        order = self.env["sale.order"].with_company(company).create({
            "partner_id": self.partner.id,
            "company_id": company.id,
            "date_order": fields.Datetime.now(),
            "order_line": [(0, 0, line)],
        })
        if currency:
            order.currency_id = currency
        order.state = state
        return order

    def _foreign_currency(self, rate=2.0):
        """Una moneda distinta de la de la empresa, con su cotización."""
        company_currency = self.company_1.currency_id
        foreign = self.env["res.currency"].with_context(active_test=False).search(
            [("id", "!=", company_currency.id)], limit=1
        )
        foreign.active = True
        self.env["res.currency.rate"].create({
            "currency_id": foreign.id,
            "company_id": self.company_1.id,
            "name": fields.Date.today() - timedelta(days=1),
            "rate": rate,
        })
        return foreign

    def _summary(self, company_ids):
        service = self.service.with_user(self.admin).with_context(allowed_company_ids=company_ids)
        return service.get_dashboard_summary("month")

    def _service(self):
        return self.service.with_user(self.admin).with_context(allowed_company_ids=[self.company_1.id])

    def test_period_ranges_are_consistent(self):
        for period in ("week", "month", "year"):
            ranges = self.service._period_ranges(period)
            current_start, current_end = ranges["current"]
            previous_start, previous_end = ranges["previous"]
            self.assertEqual(previous_end, current_start)
            self.assertLess(previous_start, previous_end)
            self.assertLess(current_start, current_end)
        self.assertEqual(self.service._period_ranges("week")["current"][0].weekday(), 0)
        self.assertEqual(self.service._period_ranges("month")["current"][0].day, 1)

    def test_summary_only_counts_selected_companies(self):
        base = self._summary([self.company_1.id])["kpis"]["sales"]["value"]
        self._make_order(self.company_1, 100)
        self._make_order(self.company_2, 100)

        only_first = self._summary([self.company_1.id])["kpis"]["sales"]["value"]
        both = self._summary([self.company_1.id, self.company_2.id])["kpis"]["sales"]["value"]

        self.assertEqual(only_first, base + 1)
        self.assertEqual(both, base + 2)

    def test_summary_converts_amounts_to_company_currency(self):
        foreign = self._foreign_currency()
        before = self._summary([self.company_1.id])["kpis"]["sales"]["total"]
        self._make_order(self.company_1, 100, currency=foreign)

        after = self._summary([self.company_1.id])
        self.assertAlmostEqual(after["kpis"]["sales"]["total"] - before, 50.0, places=2)
        self.assertEqual(after["currency"], self.company_1.currency_id.name)

    def test_summary_returns_every_kpi_key(self):
        summary = self._summary([self.company_1.id])
        self.assertEqual(
            set(summary["kpis"]), {"sales", "orders", "purchase_orders", "invoiced"}
        )
        self.assertEqual(set(summary["recent"]), set(summary["kpis"]))

    # ------------------------------------------------------------------
    # Gráfico "Presupuestos vs Pedidos"
    # ------------------------------------------------------------------
    def test_sales_chart_counts_quotations_and_orders_per_day(self):
        service = self._service()
        today = fields.Date.today().strftime("%Y-%m-%d")
        before = service.get_sales_chart("month")
        self._make_order(self.company_1, 10)
        self._make_order(self.company_1, 10)
        self._make_order(self.company_1, 10, state="draft")
        self._make_order(self.company_1, 10, state="sent")
        self._make_order(self.company_1, 10, state="cancel")

        after = service.get_sales_chart("month")

        self.assertEqual(after["orders"].get(today, 0) - before["orders"].get(today, 0), 2)
        # Los cancelados no cuentan; borradores y enviados sí son presupuestos.
        self.assertEqual(after["quotations"].get(today, 0) - before["quotations"].get(today, 0), 2)

    def test_sales_chart_year_groups_by_month(self):
        service = self._service()
        month = fields.Date.today().strftime("%Y-%m")
        before = service.get_sales_chart("year")
        self._make_order(self.company_1, 10)

        after = service.get_sales_chart("year")

        self.assertEqual(after["orders"].get(month, 0) - before["orders"].get(month, 0), 1)
        self.assertTrue(all(len(key) == 7 for key in after["orders"]))

    def test_sales_chart_aggregates_in_database_without_row_limit(self):
        """El cliente pedía hasta 10.000 pedidos y los contaba: con más salían
        cifras falsas. Ahora se agrupa en base de datos, sin límite de filas."""
        service = self._service()
        today = fields.Date.today().strftime("%Y-%m-%d")
        before = service.get_sales_chart("month")["orders"].get(today, 0)
        orders = self.env["sale.order"]
        for _index in range(3):
            orders |= self._make_order(self.company_1, 1)

        counted = service.get_sales_chart("month")["orders"].get(today, 0)

        self.assertEqual(counted - before, len(orders))
        self.assertNotIn("limit", inspect.getsource(type(service).get_sales_chart))

    def test_sales_chart_respects_access_rights(self):
        user = new_test_user(self.env, login="xtd_chart_nosale", groups="base.group_user")

        result = self.service.with_user(user).get_sales_chart("month")

        # Un interno sin acceso a ventas no recibe cifras de pedidos.
        self.assertEqual(set(result), {"quotations", "orders"})
        if not self.env["sale.order"].with_user(user).has_access("read"):
            self.assertEqual(result, {"quotations": {}, "orders": {}})

    # ------------------------------------------------------------------
    # Top de productos
    # ------------------------------------------------------------------
    def test_top_products_ranks_by_units(self):
        self._make_order(self.company_1, 1, qty=500000, product=self.product)

        top = self._service().get_top_products("month", 5)

        self.assertEqual(top[0]["id"], self.product.id)
        self.assertEqual(top[0]["qty"], 500000)
        self.assertLessEqual(len(top), 5)
        quantities = [item["qty"] for item in top]
        self.assertEqual(quantities, sorted(quantities, reverse=True))

    def test_top_products_converts_currencies(self):
        """Antes se sumaban importes de monedas distintas tal cual."""
        foreign = self._foreign_currency(rate=2.0)
        self._make_order(self.company_1, 1, qty=500000, product=self.product)
        self._make_order(self.company_1, 1, qty=500000, product=self.product, currency=foreign)

        top = self._service().get_top_products("month", 5)

        entry = next(item for item in top if item["id"] == self.product.id)
        # 500.000 en moneda de la empresa + 500.000 en la otra moneda a tipo 2 = 750.000.
        self.assertAlmostEqual(entry["amount"], 750000.0, places=2)
        self.assertEqual(entry["qty"], 1000000)

    def test_top_products_ignores_quotations_and_cancelled_orders(self):
        self._make_order(self.company_1, 1, qty=900000, product=self.product, state="draft")
        self._make_order(self.company_1, 1, qty=900000, product=self.product, state="cancel")

        top = self._service().get_top_products("month", 5)

        self.assertNotIn(self.product.id, [item["id"] for item in top])

    def test_top_products_respects_limit_and_is_safe_with_bad_input(self):
        service = self._service()

        self.assertLessEqual(len(service.get_top_products("month", 2)), 2)
        self.assertLessEqual(len(service.get_top_products("month", -3)), 5)
        self.assertIsInstance(service.get_top_products("nonsense", None), list)
