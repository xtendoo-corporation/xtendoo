# -*- coding: utf-8 -*-

from pathlib import Path

from odoo.modules.module import get_manifest
from odoo.tests.common import TransactionCase


class TestXtdTheme(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module_path = Path(__file__).resolve().parents[1]

    def test_xtd_theme_views_are_available(self):
        for xmlid in (
            "xtendoo_xtd_theme.web_layout_xtd_branding",
            "xtendoo_xtd_theme.login_layout_xtd_branding",
            "xtendoo_xtd_theme.brand_promotion_message_xtd",
            "xtendoo_xtd_theme.webclient_bootstrap_xtd_theme_color",
            "xtendoo_xtd_theme.view_users_form_simple_modif_xtd_color_scheme",
            "xtendoo_xtd_theme.view_users_form_xtd_color_scheme",
        ):
            self.assertTrue(self.env.ref(xmlid).exists())

    def test_xtd_theme_dependencies_are_installed(self):
        modules = self.env["ir.module.module"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "web_responsive",
                        "disable_odoo_online",
                        "mail_debranding",
                        "portal_debranding",
                    ],
                )
            ]
        )
        self.assertEqual(
            set(modules.mapped("name")),
            {
                "web_responsive",
                "disable_odoo_online",
                "mail_debranding",
                "portal_debranding",
            },
        )
        self.assertTrue(all(module.state == "installed" for module in modules))

    def test_xtd_theme_backend_assets_follow_web_responsive_contract(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["web.assets_backend"]

        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_menu.scss", assets)
        self.assertIn("xtendoo_xtd_theme/static/src/js/xtd_branding.esm.js", assets)
        self.assertIn("xtendoo_xtd_theme/static/src/js/xtd_color_scheme.esm.js", assets)
        self.assertNotIn(
            "xtendoo_xtd_theme/static/src/js/xtd_section_sidebar.esm.js",
            assets,
        )
        self.assertNotIn(
            "xtendoo_xtd_theme/static/src/xml/xtd_section_sidebar.xml",
            assets,
        )

    def test_xtd_theme_dark_assets_are_declared(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["web.assets_web_dark"]

        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_theme.dark.scss", assets)
        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_menu.dark.scss", assets)

    def test_xtd_theme_tour_asset_is_declared(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["web.assets_tests"]
        self.assertIn(
            "xtendoo_xtd_theme/static/tests/tours/xtd_theme_backend_tour.js",
            assets,
        )

    def test_xtd_theme_menu_scss_keeps_top_navigation(self):
        menu_scss = self.module_path / "static" / "src" / "scss" / "xtd_menu.scss"
        content = menu_scss.read_text(encoding="utf-8")

        self.assertIn(".o_menu_sections", content)
        self.assertIn(".o_grid_apps_menu__button", content)
        self.assertIn(".app-menu-container", content)
        self.assertNotIn(".xtd-section-sidebar", content)
        self.assertNotIn("xtd-has-sidebar", content)
        self.assertNotIn("padding-left: 240px", content)

    def test_xtd_theme_branding_templates_replace_visible_odoo_mentions(self):
        templates = self.env.ref("xtendoo_xtd_theme.login_layout_xtd_branding")
        arch = templates.arch_db

        self.assertIn("Powered by Xtd", arch)
        self.assertIn("Manage Xtd Databases", arch)
        self.assertNotIn("Powered by <span>Odoo</span>", arch)

    def test_xtd_theme_theme_color_matches_xtd_palette(self):
        templates_path = self.module_path / "views" / "webclient_templates.xml"
        content = templates_path.read_text(encoding="utf-8")

        self.assertIn("'#151515' if color_scheme == 'dark' else '#ff4f00'", content)

    def test_xtd_theme_pos_assets_are_declared(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["point_of_sale._assets_pos"]
        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_pos.scss", assets)

