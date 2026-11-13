# -*- coding: utf-8 -*-

from pathlib import Path

from odoo.modules.module import get_manifest
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

MODULE = "xtendoo_xtd_theme"
MODULE_PATH = Path(__file__).resolve().parents[1]
SCSS = MODULE_PATH / "static" / "src" / "scss"


def _scss(name):
    return (SCSS / name).read_text(encoding="utf-8")


class TestXtdUiContracts(TransactionCase):
    """Reglas de interfaz que ya se rompieron una vez."""

    def test_today_highlight_is_scoped_to_today_cell(self):
        """La vista anual (Ausencias) pintaba todos los días como "hoy" porque
        la variable se definía en toda la vista."""
        content = _scss("xtd_calendar.scss")
        block = content[content.index(".fc-dayGridMonth-view {"):]
        today = block.index(".fc-day-today {")
        variable = block.index("--o-cw-bg: var(--xtd-cal-accent);")

        self.assertLess(today, variable)
        self.assertLess(variable, block.index("}", today))

    def test_chrome_stays_below_dialogs(self):
        """Barra y menú lateral por debajo del fondo de los diálogos (1050):
        con más, tapaban el borde superior de "Buscar más"."""
        content = _scss("xtd_sidebar_toggle.scss")
        import re

        for value in re.findall(r"z-index:\s*(\d+)", content):
            self.assertLess(int(value), 1050)

    def test_dialog_body_keeps_padding_unless_it_holds_a_view(self):
        content = _scss("xtd_modal.scss")

        self.assertIn("padding: 1rem 1.5rem;", content)
        self.assertIn("&:has(.o_form_view),", content)
        self.assertNotIn(".modal-body {\n        padding: 0;\n    }", content)

    def test_sidebar_widens_while_reordering(self):
        content = _scss("xtd_sidebar_toggle.scss")

        self.assertIn("$xtd-sidebar-reorder-width: 360px;", content)
        self.assertIn(".xtd-sidebar-panel:has(.xtd-sidebar-settings--active)", content)
        self.assertIn("width: $xtd-sidebar-reorder-width !important;", content)

    def test_selected_rows_use_brand_tint_in_both_schemes(self):
        light = _scss("xtd_theme.scss")
        dark = _scss("xtd_theme.dark.scss")

        self.assertIn("--xtd-selected:", light)
        self.assertIn("--xtd-selected:", dark)
        self.assertIn(".o_web_client .table-info {", light)
        self.assertIn("box-shadow: inset 0 0 0 9999px var(--xtd-selected) !important;", light)

    def test_list_footer_background_spans_full_width(self):
        content = _scss("xtd_theme.scss")

        self.assertIn(".o_list_renderer .o_list_table tfoot {", content)
        self.assertIn("inset 0 0 0 9999px var(--xtd-list-foot-bg", content)
        # Nada de pseudo-elementos anchos: generaban scroll horizontal.
        self.assertNotIn("width: 100vw", content)

    def test_navbar_search_box_is_not_stretched(self):
        content = _scss("xtd_menu.scss")
        block = content[content.index(".o_main_navbar .o_xtd_navbar_search {"):]

        self.assertIn("align-items: center;", block[:300])
        self.assertIn("height: 34px;", block)

    def test_dashboards_are_inverted_in_dark_mode(self):
        content = _scss("xtd_surfaces.dark.scss")

        self.assertIn(".o_spreadsheet_dashboard_action", content)
        self.assertIn("filter: invert(0.9) hue-rotate(180deg);", content)

    def test_pos_dark_bundle_is_declared(self):
        assets = get_manifest(MODULE)["assets"]["point_of_sale.assets_prod_dark"]

        self.assertIn(("include", f"{MODULE}.assets_dark_variables"), assets)
        self.assertIn(f"{MODULE}/static/src/scss/xtd_pos.dark.scss", assets)

    def test_login_keeps_core_integrations(self):
        arch = self.env.ref(f"{MODULE}.login_xtd", raise_if_not_found=False)
        if not arch:
            arch = self.env["ir.ui.view"].search([
                ("key", "like", f"{MODULE}.%"),
                ("inherit_id", "=", self.env.ref("web.login").id),
            ], limit=1)
        self.assertTrue(arch)
        content = arch.arch_db

        self.assertIn('t-call="web.login_oauth"', content)
        self.assertIn("o_caps_lock_warning", content)
        self.assertIn("/web/signup", content)
        self.assertIn("/web/become", content)


@tagged("post_install", "-at_install")
class TestXtdDarkPosAssets(TransactionCase):
    def test_pos_dark_bundle_compiles_dark(self):
        if "pos.config" not in self.env:
            self.skipTest("Se necesita point_of_sale")
        qweb = self.env["ir.qweb"]
        files, _external = qweb._get_asset_content("point_of_sale.assets_prod_dark")
        urls = [asset["url"] for asset in files]
        primary = f"/{MODULE}/static/src/scss/variables/primary_variables.dark.scss"
        self.assertIn(primary, urls)
        self.assertLess(urls.index(primary), urls.index("/web/static/src/scss/primary_variables.scss"))

        bundle = qweb._get_asset_bundle("point_of_sale.assets_prod_dark", css=True, js=False)
        attachments = bundle.css()
        self.assertFalse(bundle.css_errors, "\n".join(bundle.css_errors))
        css = "\n".join(attachment.raw.decode("utf-8") for attachment in attachments)
        self.assertNotIn("css_error_message", css)
        self.assertIn(".login-overlay", css)

        light_files, _external = qweb._get_asset_content("point_of_sale.assets_prod")
        self.assertNotIn(primary, [asset["url"] for asset in light_files])


@tagged("post_install", "-at_install")
class TestXtdPosColorSchemeCookie(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, login="xtd_pos_scheme", password="xtd_pos_scheme", groups="base.group_user"
        )

    def _pos_cookie_for(self, scheme):
        self.user.color_scheme = scheme
        self.authenticate(self.user.login, "xtd_pos_scheme")
        response = self.url_open("/odoo")
        return response.cookies.get("pos_color_scheme")

    def test_pos_cookie_follows_dark_preference(self):
        self.assertEqual(self._pos_cookie_for("dark"), "dark")

    def test_pos_cookie_follows_light_preference(self):
        self.assertEqual(self._pos_cookie_for("light"), "light")
