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

    def test_xtd_theme_mobile_sidebar_toggle_is_preserved(self):
        navbar_js = (
            self.module_path
            / "static"
            / "src"
            / "js"
            / "xtd_navbar_sidebar.esm.js"
        ).read_text(encoding="utf-8")
        navbar_xml = (
            self.module_path / "static" / "src" / "xml" / "xtd_navbar.xml"
        ).read_text(encoding="utf-8")

        self.assertIn("APP_MENU:TOGGLE_SIDEBAR", navbar_js)
        self.assertIn("_syncXtdMobileSidebarVisibility", navbar_js)
        self.assertIn("this.state.isAppMenuSidebarOpened = !this.ui.isSmall", navbar_js)
        self.assertIn("onXtdAppsButtonClick", navbar_xml)

        sidebar_scss = (
            self.module_path
            / "static"
            / "src"
            / "scss"
            / "xtd_sidebar_toggle.scss"
        ).read_text(encoding="utf-8")
        self.assertIn("top: 0 !important;", sidebar_scss)
        self.assertIn(
            "padding-top: calc(var(--o-navbar-height, 50px) + 32px) !important;",
            sidebar_scss,
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

        self.assertIn(".o_grid_apps_menu__button", content)
        self.assertIn(".app-menu-container", content)
        self.assertIn("--NavBar-brand-color", content)
        self.assertIn("--NavBar-menuToggle-color", content)
        self.assertIn("--NavBar-entry-color--active", content)
        self.assertIn("--NavBar-entry-borderColor-active", content)
        self.assertIn("--NavBar-entry-backgroundColor--active", content)
        self.assertIn("--NavBar-entry-backgroundColor--hover", content)
        self.assertIn("--NavBar-entry-backgroundColor--focus", content)
        self.assertIn('.dropdown.show > .dropdown-toggle:not(.o-dropdown-toggle-custo)', content)
        self.assertIn('.o_nav_entry[aria-expanded="true"]', content)
        self.assertIn('.o_grid_apps_menu__button[aria-expanded="true"]', content)
        self.assertIn('.o_main_navbar {\n    .dropdown-menu {', content)
        self.assertIn('.o_menu_brand,', content)
        self.assertIn('.o_main_navbar .o_menu_brand {', content)
        self.assertIn('border-bottom: 0 !important;', content)
        self.assertIn('.o_main_navbar::after {', content)
        self.assertIn('text-decoration: none !important;', content)
        self.assertIn('font-size: 1rem !important;', content)
        self.assertIn('line-height: 1.2 !important;', content)
        self.assertIn('min-height: 28px !important;', content)
        self.assertIn('height: 28px !important;', content)
        self.assertIn('padding-left: 0.95rem !important;', content)
        self.assertIn('a.o_menu_brand.o-dropdown-item.dropdown-item:hover', content)
        self.assertIn('.o_menu_systray {', content)
        self.assertIn('> li > button', content)
        self.assertNotIn(".xtd-section-sidebar", content)
        self.assertNotIn("xtd-has-sidebar", content)
        self.assertNotIn("padding-left: 240px", content)
        self.assertNotIn(".o_main_navbar .o_menu_brand::before", content)
        self.assertNotIn("border-bottom: 2px solid transparent", content)
        self.assertNotIn(".o_menu_sections .dropdown-menu", content)

    def test_xtd_theme_branding_templates_replace_visible_odoo_mentions(self):
        templates = self.env.ref("xtendoo_xtd_theme.login_layout_xtd_branding")
        arch = templates.arch_db

        self.assertIn("Powered by Xtd", arch)
        self.assertIn("Manage Xtd Databases", arch)
        self.assertNotIn("Powered by <span>Odoo</span>", arch)

    def test_xtd_theme_dark_menu_scss_keeps_navbar_titles_without_underline(self):
        dark_menu_scss = self.module_path / "static" / "src" / "scss" / "xtd_menu.dark.scss"
        content = dark_menu_scss.read_text(encoding="utf-8")

        self.assertIn(".o_menu_brand,", content)
        self.assertIn(".o_main_navbar .o_menu_brand {", content)
        self.assertIn("border-bottom: 0 !important;", content)
        self.assertIn(".o_main_navbar::after {", content)
        self.assertIn("min-height: 28px !important;", content)
        self.assertIn("border-radius: 10px !important;", content)
        self.assertIn("a.o_menu_brand.o-dropdown-item.dropdown-item:hover", content)
        self.assertIn(".o-dropdown-item,", content)
        self.assertIn("text-decoration: none !important;", content)
        self.assertIn("font-size: 1rem !important;", content)
        self.assertIn("line-height: 1.2 !important;", content)
        self.assertIn("min-height: 28px !important;", content)
        self.assertIn("height: 28px !important;", content)
        self.assertIn(".o_menu_systray {", content)
        self.assertIn("> li > button", content)

    def test_xtd_theme_theme_color_matches_xtd_palette(self):
        templates_path = self.module_path / "views" / "webclient_templates.xml"
        content = templates_path.read_text(encoding="utf-8")

        self.assertIn("'#151515' if color_scheme == 'dark' else '#ff4f00'", content)

    def test_xtd_theme_icons_use_global_black_palette(self):
        theme_scss = self.module_path / "static" / "src" / "scss" / "xtd_theme.scss"
        content = theme_scss.read_text(encoding="utf-8")

        self.assertIn('.o_web_client :is(i,span,a,button,div).fa', content)
        self.assertIn('.o_web_client :is(i,span,a,button,div).oi', content)
        self.assertIn('color:var(--xtd-ink)!important', content)
        self.assertIn('.o_web_client :is(.btn-primary,.btn-danger,.btn-success,.btn-warning,.btn-info,.o_form_button_save,.o_list_button_add,.o_control_panel .o-kanban-button-new)', content)
        self.assertIn('color:inherit!important', content)

    def test_xtd_theme_dark_icons_keep_readable_contrast(self):
        dark_theme_scss = self.module_path / "static" / "src" / "scss" / "xtd_theme.dark.scss"
        content = dark_theme_scss.read_text(encoding="utf-8")

        self.assertIn('.o_web_client :is(i,span,a,button,div).fa,', content)
        self.assertIn('color: var(--xtd-ink) !important;', content)
        self.assertIn('color: inherit !important;', content)

    def test_xtd_theme_dark_backend_surfaces_follow_enterprise_like_contract(self):
        dark_theme_scss = self.module_path / "static" / "src" / "scss" / "xtd_theme.dark.scss"
        content = dark_theme_scss.read_text(encoding="utf-8")

        self.assertIn("--xtd-deep: #1b1d26;", content)
        self.assertIn("--xtd-surface: #262a36;", content)
        self.assertIn(".o_web_client > .o_action_manager,", content)
        self.assertIn(".o_list_button_add,", content)
        self.assertIn("background: var(--o-brand-primary) !important;", content)
        self.assertIn(".o_form_view {", content)
        self.assertIn(".o_notification_manager {", content)
        self.assertIn("--Notification__background-color: var(--xtd-surface) !important;", content)
        self.assertIn(".o_notification_close,", content)
        self.assertIn(".o_field_x2many .o_kanban_renderer .o-kanban-button-new,", content)
        self.assertIn("background: var(--xtd-surface-soft) !important;", content)
        self.assertIn("width: 100% !important;", content)
        self.assertIn("color: var(--xtd-link) !important;", content)
        self.assertIn(".o_field_widget .o_kanban_view.o_field_x2many_kanban,", content)
        self.assertIn("--Kanban-background: transparent !important;", content)
        self.assertIn(".o_field_widget .o_kanban_view.o_field_x2many_kanban .o_kanban_renderer.o_kanban_ungrouped .o_kanban_record", content)
        self.assertIn("background: transparent !important;", content)
        self.assertIn("border-radius: 0 !important;", content)
        self.assertIn("flex: 0 0 24rem !important;", content)
        self.assertIn("width: 24rem !important;", content)
        self.assertIn(".o_kanban_record.flex-row:not(.o-kanban-button-new)", content)
        self.assertIn("flex: 0 0 2.25rem !important;", content)
        self.assertIn("margin-left: auto !important;", content)
        self.assertIn(".o_form_sheet {", content)
        self.assertIn(".o_form_statusbar {", content)
        self.assertIn(".o_field_statusbar > .o_statusbar_status", content)
        self.assertIn(".o_notebook {", content)
        self.assertIn(".o-mail-Form-chatter,", content)
        self.assertIn(".o-mail-Chatter-top {", content)
        self.assertIn(".o-mail-Chatter-sendMessage,", content)
        self.assertIn(".o-mail-Message-author,", content)
        self.assertIn(".o-mail-Message-trackingNew,", content)
        self.assertIn(".o_list_renderer .o_list_table", content)
        self.assertIn(".o_list_renderer .o_list_table tfoot", content)
        self.assertIn(".o_form_view .o_field_x2many .o_list_table thead th,", content)
        self.assertIn("color: #ffffff !important;", content)
        self.assertIn(".o_control_panel .o_cp_pager .btn", content)
        self.assertIn(".o_list_renderer .o_list_table thead button,", content)
        self.assertIn(".o_searchview_facet", content)
        self.assertIn("--SearchBar-facet-background: var(--xtd-surface) !important;", content)
        self.assertIn(".o_kanban_renderer {", content)
        self.assertIn(".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost),", content)
        self.assertIn(".dropdown-menu,", content)
        self.assertIn(".badge.text-bg-light,", content)

    def test_xtd_theme_settings_scss_scopes_primary_states(self):
        theme_scss = self.module_path / "static" / "src" / "scss" / "xtd_theme.scss"
        content = theme_scss.read_text(encoding="utf-8")

        self.assertIn("--bs-primary-bg-subtle:#f7f5f2", content)
        self.assertIn(".o_base_settings_view .settings_tab .tab.current", content)
        self.assertIn(".o_base_settings_view .settings_tab .tab.bg-primary-subtle", content)
        self.assertIn(".o_base_settings_view .settings .bg-primary-subtle", content)
        self.assertIn("@media (max-width:767.98px)", content)
        self.assertNotIn(
            ".text-bg-primary{color:#fff!important;background-color:rgba(var(--bs-primary-rgb),1)!important}",
            content,
        )

    def test_xtd_theme_pos_assets_are_declared(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["point_of_sale._assets_pos"]
        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_pos.scss", assets)
