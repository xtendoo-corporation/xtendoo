# -*- coding: utf-8 -*-

from odoo.modules.module import get_manifest
from odoo.tests.common import TransactionCase


class TestXtdTheme(TransactionCase):
    def test_xtd_theme_views_are_available(self):
        for xmlid in (
            "xtendoo_xtd_theme.web_layout_xtd_branding",
            "xtendoo_xtd_theme.login_layout_xtd_branding",
            "xtendoo_xtd_theme.brand_promotion_message_xtd",
        ):
            self.assertTrue(self.env.ref(xmlid).exists())

    def test_xtd_theme_dependencies_are_installed(self):
        modules = self.env["ir.module.module"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "disable_odoo_online",
                        "mail_debranding",
                        "portal_debranding",
                    ],
                )
            ]
        )
        self.assertEqual(set(modules.mapped("name")), {
            "disable_odoo_online",
            "mail_debranding",
            "portal_debranding",
        })
        self.assertTrue(all(module.state == "installed" for module in modules))

    def test_xtd_theme_pos_assets_are_declared(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        self.assertIn(
            "xtendoo_xtd_theme/static/src/scss/xtd_pos.scss",
            manifest["assets"]["point_of_sale._assets_pos"],
        )
