# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestXtdDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref("base.user_admin").sudo()

    def test_default_dashboard_blocks_are_available(self):
        blocks = self.env["xtd.dashboard.block"].search([])

        self.assertTrue(blocks)
        self.assertIn("main_kpis", blocks.mapped("technical_key"))
        self.assertIn("sales_chart", blocks.mapped("technical_key"))
        self.assertIn("pending_activities", blocks.mapped("technical_key"))
        self.assertIn("top_products", blocks.mapped("technical_key"))
        self.assertIn("order_status", blocks.mapped("technical_key"))

    def test_dashboard_service_returns_global_layout_by_default(self):
        layout = self.env["xtd.dashboard.service"].get_dashboard_layout()

        self.assertEqual(layout["mode"], "global")
        self.assertTrue(layout["blocks"])
        self.assertEqual(layout["blocks"][0]["component"], "main_kpis")

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
