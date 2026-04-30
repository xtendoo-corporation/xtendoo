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
                        "web_responsive",
                        "disable_odoo_online",
                        "mail_debranding",
                        "portal_debranding",
                    ],
                )
            ]
        )
        self.assertEqual(set(modules.mapped("name")), {
            "web_responsive",
            "disable_odoo_online",
            "mail_debranding",
            "portal_debranding",
        })
        self.assertTrue(all(module.state == "installed" for module in modules))

    def test_xtd_theme_menu_scss_is_declared(self):
        """xtd_menu.scss debe estar declarado en web.assets_backend."""
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["web.assets_backend"]
        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_menu.scss", assets)

    def test_xtd_theme_menu_scss_contains_sidebar_styles(self):
        """xtd_menu.scss debe transformar el panel de apps en sidebar lateral."""
        module_path = Path(__file__).resolve().parents[1]
        menu_scss = module_path / "static" / "src" / "scss" / "xtd_menu.scss"
        content = menu_scss.read_text(encoding="utf-8")

        # Panel convertido a sidebar (ancho fijo, no fullscreen)
        self.assertIn(".app-menu-container", content)
        self.assertIn("280px", content)
        # Lista vertical en lugar de grid
        self.assertIn(".o-app-menu-list", content)
        self.assertIn("flex-direction: column", content)
        # Ítems en fila horizontal
        self.assertIn(".o-app-menu-item", content)
        self.assertIn("flex-direction: row", content)
        # Sección del navbar estilizada
        self.assertIn(".o_menu_sections", content)
        self.assertIn(".o_nav_entry", content)

    def test_xtd_theme_navbar_scss_contains_brand_chip(self):
        """xtd_menu.scss debe estilizar el chip de app activa y el botón de apps."""
        module_path = Path(__file__).resolve().parents[1]
        menu_scss = module_path / "static" / "src" / "scss" / "xtd_menu.scss"
        content = menu_scss.read_text(encoding="utf-8")

        # Altura del navbar ampliada
        self.assertIn("--o-navbar-height: 52px", content)
        # Chip de la app activa
        self.assertIn(".o_menu_brand", content)
        # Indicador de sección activa con línea inferior
        self.assertIn("border-bottom", content)
        # Botón de apps
        self.assertIn(".o_grid_apps_menu__button", content)
        # Sidebar móvil estilizado
        self.assertIn(".o_app_menu_sidebar", content)

    def test_xtd_theme_section_sidebar_assets_declared(self):
        """El JS y XML del sidebar de secciones deben estar en web.assets_backend."""
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["web.assets_backend"]
        self.assertIn(
            "xtendoo_xtd_theme/static/src/js/xtd_section_sidebar.esm.js",
            assets,
        )
        self.assertIn(
            "xtendoo_xtd_theme/static/src/xml/xtd_section_sidebar.xml",
            assets,
        )

    def test_xtd_theme_section_sidebar_js_structure(self):
        """El JS del sidebar debe registrarse en main_components y usar menuService."""
        module_path = Path(__file__).resolve().parents[1]
        sidebar_js = (
            module_path / "static" / "src" / "js" / "xtd_section_sidebar.esm.js"
        )
        content = sidebar_js.read_text(encoding="utf-8")

        # Registrado en el registry correcto
        self.assertIn('registry.category("main_components")', content)
        self.assertIn('"xtd_section_sidebar"', content)
        # Usa el servicio de menú estándar de Odoo
        self.assertIn('useService("menu")', content)
        # Gestión del ciclo de vida OWL
        self.assertIn("onMounted", content)
        self.assertIn("onPatched", content)
        self.assertIn("onWillUnmount", content)
        # Body class para el offset CSS
        self.assertIn("xtd-has-sidebar", content)

    def test_xtd_theme_section_sidebar_xml_structure(self):
        """El XML del sidebar debe incluir el template principal y el nodo recursivo."""
        module_path = Path(__file__).resolve().parents[1]
        sidebar_xml = (
            module_path / "static" / "src" / "xml" / "xtd_section_sidebar.xml"
        )
        content = sidebar_xml.read_text(encoding="utf-8")

        # Templates esperados
        self.assertIn("xtendoo_xtd_theme.SectionSidebar", content)
        self.assertIn("xtendoo_xtd_theme.SidebarNode", content)
        # Clases CSS definidas
        self.assertIn("xtd-section-sidebar", content)
        self.assertIn("xtd-sidebar-header", content)
        self.assertIn("xtd-sidebar-group", content)
        self.assertIn("xtd-sidebar-item", content)
        # Recursividad del nodo
        self.assertIn("node.childrenTree", content)

    def test_xtd_theme_section_sidebar_scss_offset(self):
        """El SCSS debe contener el offset de contenido y estilos del sidebar."""
        module_path = Path(__file__).resolve().parents[1]
        menu_scss = module_path / "static" / "src" / "scss" / "xtd_menu.scss"
        content = menu_scss.read_text(encoding="utf-8")

        # Clase body para offset
        self.assertIn("body.xtd-has-sidebar", content)
        self.assertIn("padding-left: 240px", content)
        # Sidebar fijo
        self.assertIn(".xtd-section-sidebar", content)
        self.assertIn("position: fixed", content)
        # Items de menú
        self.assertIn(".xtd-sidebar-item", content)
        self.assertIn(".xtd-sidebar-group", content)
        # Estado activo (BEM nesting: &--active dentro de .xtd-sidebar-item)
        self.assertIn("&--active", content)

    def test_xtd_theme_pos_assets_are_declared(self):
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["point_of_sale._assets_pos"]
        self.assertIn("xtendoo_xtd_theme/static/src/scss/xtd_pos.scss", assets)

    def test_xtd_theme_res_config_edition_asset_not_declared(self):
        """res_config_edition.xml depends on a web_enterprise-only QWeb template
        and must not be registered as an asset when using web_responsive."""
        manifest = get_manifest("xtendoo_xtd_theme")
        assets = manifest["assets"]["web.assets_backend"]
        self.assertNotIn(
            "xtendoo_xtd_theme/static/src/xml/res_config_edition.xml",
            assets,
        )


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

    def test_xtd_theme_form_selectors_use_xtd_ink(self):
        module_path = Path(__file__).resolve().parents[1]
        theme_scss = module_path / "static" / "src" / "scss" / "xtd_theme.scss"
        content = theme_scss.read_text(encoding="utf-8")

        self.assertIn(".form-check-input:checked", content)
        self.assertIn("background-color:var(--xtd-ink)!important", content)
        self.assertIn("border-color:var(--xtd-ink)!important", content)

    def test_xtd_theme_loading_indicator_uses_xtd_ink(self):
        module_path = Path(__file__).resolve().parents[1]
        theme_scss = module_path / "static" / "src" / "scss" / "xtd_theme.scss"
        content = theme_scss.read_text(encoding="utf-8")

        self.assertIn(".o_loading_indicator", content)
        self.assertIn(
            ".o_loading_indicator{background-color:var(--xtd-ink)!important",
            content,
        )

    def test_xtd_theme_activity_popover_button_is_compact(self):
        module_path = Path(__file__).resolve().parents[1]
        theme_scss = module_path / "static" / "src" / "scss" / "xtd_theme.scss"
        content = theme_scss.read_text(encoding="utf-8")

        self.assertIn(".o-mail-ActivityListPopover > .btn", content)
        self.assertIn("padding:.7rem 1rem!important", content)
        self.assertIn("font-size:.95rem!important", content)

    def test_xtd_theme_required_fields_underline_only_when_invalid(self):
        module_path = Path(__file__).resolve().parents[1]
        theme_scss = module_path / "static" / "src" / "scss" / "xtd_theme.scss"
        content = theme_scss.read_text(encoding="utf-8")

        self.assertIn(".o_field_invalid", content)
        self.assertIn("--o-input-border-color:var(--xtd-orange)", content)
        self.assertIn("border-width:0 0 1px 0!important", content)
        self.assertNotIn(".o_required_modifier.o_input", content)
