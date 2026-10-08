# -*- coding: utf-8 -*-

import unittest
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
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
        cls.company_2 = cls.env["res.company"].search([("id", "!=", cls.company_1.id)], limit=1)
        if not cls.company_2:
            raise unittest.SkipTest("Se necesita una segunda empresa en la base de datos")
        cls.admin = cls.env.ref("base.user_admin")
        cls.admin.company_ids |= cls.company_2
        # Un cliente sin empresa asignada vale para pedidos de cualquier empresa.
        cls.partner = cls.env["res.partner"].search([("company_id", "=", False)], limit=1)
        cls.service = cls.env["xtd.dashboard.service"]

    def _make_order(self, company, amount, currency=None):
        order = self.env["sale.order"].with_company(company).create({
            "partner_id": self.partner.id,
            "company_id": company.id,
            "date_order": fields.Datetime.now(),
            "order_line": [(0, 0, {
                "name": "Servicio",
                "product_uom_qty": 1,
                "price_unit": amount,
                "tax_ids": [(5, 0, 0)],
            })],
        })
        if currency:
            order.currency_id = currency
        order.state = "sale"
        return order

    def _summary(self, company_ids):
        service = self.service.with_user(self.admin).with_context(allowed_company_ids=company_ids)
        return service.get_dashboard_summary("month")

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
        company_currency = self.company_1.currency_id
        foreign = self.env["res.currency"].with_context(active_test=False).search(
            [("id", "!=", company_currency.id)], limit=1
        )
        foreign.active = True
        self.env["res.currency.rate"].create({
            "currency_id": foreign.id,
            "company_id": self.company_1.id,
            "name": fields.Date.today() - timedelta(days=1),
            "rate": 2.0,
        })
        before = self._summary([self.company_1.id])["kpis"]["sales"]["total"]
        self._make_order(self.company_1, 100, currency=foreign)

        after = self._summary([self.company_1.id])
        self.assertAlmostEqual(after["kpis"]["sales"]["total"] - before, 50.0, places=2)
        self.assertEqual(after["currency"], company_currency.name)

    def test_summary_returns_every_kpi_key(self):
        summary = self._summary([self.company_1.id])
        self.assertEqual(
            set(summary["kpis"]), {"sales", "orders", "purchase_orders", "invoiced"}
        )
        self.assertEqual(set(summary["recent"]), set(summary["kpis"]))
