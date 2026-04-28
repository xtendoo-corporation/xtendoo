# -*- coding: utf-8 -*-

from pathlib import Path

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
        assets = manifest["assets"]["point_of_sale._assets_pos"]
        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_pos.scss", assets)

    def test_xtd_theme_pos_logos_use_safe_css_override(self):
        module_path = Path(__file__).resolve().parents[1]
        pos_scss = module_path / "static" / "src" / "scss" / "xtd_pos.scss"
        content = pos_scss.read_text(encoding="utf-8")

        self.assertIn(".pos-logo", content)
        self.assertIn("/xtendoo_xtd_theme/static/src/img/xtd_logo.svg", content)
        self.assertNotIn("--navbar-logo", content)

    def test_xtd_theme_pos_primary_buttons_follow_backend_colors(self):
        module_path = Path(__file__).resolve().parents[1]
        pos_scss = module_path / "static" / "src" / "scss" / "xtd_pos.scss"
        content = pos_scss.read_text(encoding="utf-8")

        self.assertIn(
            ".pos .btn-primary,.pos .button.btn-primary,"
            ".pos .pay-order-button,.pos .validation-button.next,",
            content,
        )
        self.assertIn("background:var(--xtd-ink)!important", content)
        self.assertIn(
            ".pos .btn-primary:hover,.pos .button.btn-primary:hover,"
            ".pos .pay-order-button:hover,",
            content,
        )
        self.assertIn("background:var(--xtd-burgundy)!important", content)
