# -*- coding: utf-8 -*-

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
        self.assertNotIn("sale_recent_quotes", [block["key"] for block in layout["available_blocks"]])

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

    def test_dashboard_service_creates_custom_list_block(self):
        service = self.env["xtd.dashboard.service"]

        layout = service.create_custom_block({
            "name": "Usuarios recientes",
            "block_type": "generic_list",
            "model": "res.users",
            "fields": "name,login",
            "limit": 3,
            "size": "medium",
        })

        self.assertIn("Usuarios recientes", [block["name"] for block in layout["blocks"]])
        block = self.env["xtd.dashboard.block"].search([("name", "=", "Usuarios recientes")], limit=1)
        self.assertEqual(block.component, "generic_list")
        self.assertEqual(block.config["fields"], ["name", "login"])

    def test_dashboard_service_creates_custom_kanban_block(self):
        service = self.env["xtd.dashboard.service"]

        layout = service.create_custom_block({
            "name": "Contactos kanban",
            "block_type": "generic_kanban",
            "model": "res.partner",
            "fields": ["display_name", "email", "phone"],
            "limit": 6,
            "size": "large",
        })

        created_blocks = [block for block in layout["blocks"] if block["name"] == "Contactos kanban"]
        self.assertTrue(created_blocks)
        self.assertEqual(created_blocks[0]["component"], "generic_kanban")
        self.assertTrue(created_blocks[0]["can_delete"])
