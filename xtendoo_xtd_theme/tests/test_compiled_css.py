# -*- coding: utf-8 -*-

import re

from odoo.tests import TransactionCase, tagged


def _compile(env, bundle_name):
    bundle = env["ir.qweb"]._get_asset_bundle(bundle_name, css=True, js=False)
    attachments = bundle.css()
    assert not bundle.css_errors, "\n".join(bundle.css_errors)
    css = "\n".join(attachment.raw.decode("utf-8") for attachment in attachments)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)  # los comentarios con la ruta del fichero
    css = re.sub(r"\s+", " ", css)
    # Un único formato: el compilador no escribe igual todas las reglas.
    for source, target in ((": ", ":"), (" {", "{"), ("; ", ";"), (" !important", "!important"), ("{ ", "{")):
        css = css.replace(source, target)
    return css


def _declarations(css, selector):
    """Declaraciones de todas las reglas cuya lista de selectores incluye
    ``selector`` (CSS ya compilado: no depende de cómo esté escrito el SCSS)."""
    found = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [item.strip() for item in match.group(1).split(",")]
        if selector in selectors:
            found.append(match.group(2))
    return found


@tagged("post_install", "-at_install")
class TestXtdThemeCompiledCss(TransactionCase):
    """Comportamiento del tema comprobado sobre el CSS que recibe el navegador.

    Sustituye a las comprobaciones de texto sobre los ficheros SCSS: aquellas
    se rompían con cualquier reorganización aunque el resultado fuese igual.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.light = _compile(cls.env, "web.assets_web")
        cls.dark = _compile(cls.env, "web.assets_web_dark")
        cls.frontend = _compile(cls.env, "web.assets_frontend")

    def assertRule(self, css, selector, *fragments):
        rules = _declarations(css, selector)
        self.assertTrue(rules, f"No hay ninguna regla para {selector}")
        for fragment in fragments:
            self.assertTrue(
                any(fragment in rule for rule in rules),
                f"{selector} no declara {fragment}",
            )

    def test_brand_tokens_and_primary_button_in_light(self):
        self.assertRule(self.light, ":root", "--xtd-orange:#f45700", "--xtd-ink:#151515")
        # Acción principal en negro con hover burdeos.
        self.assertRule(self.light, ".btn-primary", "background:var(--xtd-ink)")
        self.assertRule(self.light, ".btn-primary:hover", "background:var(--xtd-burgundy)")

    def test_dark_scheme_redefines_tokens_and_uses_brand_accent(self):
        self.assertRule(self.dark, ":root", "--xtd-paper:#1a1918", "--xtd-orange:#ff7a3d")
        self.assertRule(self.dark, ".btn-primary", "background:var(--o-brand-primary)")

    def test_navbar_and_sidebar_use_chrome_surface_in_dark(self):
        self.assertRule(self.dark, ".o_main_navbar", "background:var(--xtd-chrome)")
        self.assertRule(self.dark, ".o_app_menu_sidebar", "background:var(--xtd-chrome)")

    def test_sidebar_layout_in_both_schemes(self):
        for css in (self.light, self.dark):
            self.assertRule(css, ".xtd-sidebar-panel", "width:280px", "z-index:1040")

    def test_status_icon_colours_are_kept_in_both_schemes(self):
        """Los iconos van en el color del texto, pero los de estado (presencia,
        actividades) conservan su color propio."""
        for scheme, css in (("light", self.light), ("dark", self.dark)):
            for status in ("text-success", "text-warning", "text-danger"):
                with self.subTest(scheme=scheme, status=status):
                    self.assertRegex(
                        css,
                        rf"\.{status}:is\([^)]*\)\{{color:#[0-9a-f]{{6}}!important",
                    )

    def test_dark_dialogs_dropdowns_and_notifications_are_raised_surfaces(self):
        self.assertRule(self.dark, ".modal-content", "background:var(--xtd-raised)")
        self.assertRule(self.dark, ".dropdown-menu", "background:var(--xtd-raised)")
        self.assertRule(
            self.dark, ".o_notification_manager .o_notification",
            "background:var(--xtd-surface)",
        )

    def test_login_heading_is_centered_and_has_mobile_rules(self):
        self.assertRule(self.frontend, ".xtd-login-heading", "text-align:center")
        self.assertIn("max-width:767.98px", self.frontend)

    def test_dark_mode_does_not_leak_into_light_bundle(self):
        self.assertNotIn("--xtd-chrome", self.light)
        self.assertNotIn("--xtd-raised", self.light)

    def test_form_links_are_calm_and_priority_stars_keep_their_colour(self):
        for scheme, css in (("light", self.light), ("dark", self.dark)):
            with self.subTest(scheme=scheme):
                self.assertRegex(css, r"\.o_form_view a\.o_form_uri:not\(\.btn\)[^{]*\{color:var\(--xtd-ink\)!important")
                self.assertRule(css, ".o_web_client .o_priority a.o_priority_star.fa-star", "color:var(--xtd-star)!important")
        self.assertRule(self.light, ":root", "--xtd-star:#f0ad00")
        self.assertRule(self.dark, ":root", "--xtd-star:#ffd166")

    def test_scrollbars_are_neutral_and_only_orange_on_hover(self):
        for scheme, css in (("light", self.light), ("dark", self.dark)):
            with self.subTest(scheme=scheme):
                self.assertRule(css, "*", "scrollbar-color:var(--xtd-scroll) transparent")
                self.assertRule(css, "::-webkit-scrollbar-thumb", "background:var(--xtd-scroll)")
                self.assertRule(css, "::-webkit-scrollbar-thumb:hover", "background:var(--xtd-orange)")
        self.assertRule(self.light, ":root", "--xtd-scroll:rgba(21,21,21,.22)")
        self.assertRule(self.dark, ":root", "--xtd-scroll:rgba(233, 229, 223, 0.22)")

    def test_searchview_and_filter_toggle_form_one_pill(self):
        self.assertRule(
            self.light, ".o_control_panel .o_cp_searchview",
            "border-radius:999px", "overflow:hidden",
        )
        self.assertRule(
            self.light, ".o_control_panel .o_cp_searchview:focus-within",
            "border-color:var(--xtd-orange, #f45700)",
        )
        self.assertRule(
            self.light, ".o_control_panel .o_cp_searchview .o_searchview_dropdown_toggler",
            "border:0!important", "border-radius:0!important",
        )

    def test_current_breadcrumb_is_ink_not_link_colour(self):
        self.assertRule(
            self.light, ".o_control_panel .o_last_breadcrumb_item",
            "color:var(--xtd-ink, #151515)", "font-weight:600",
        )

    def test_dashboard_activity_date_is_a_single_line_pill(self):
        self.assertRule(
            self.light, ".o_xtd_dashboard .activity-item .text-danger.x-small",
            "white-space:nowrap", "border-radius:999px",
        )

    def test_form_list_amount_column_stays_visible(self):
        self.assertRule(
            self.light, '.o_form_view .o_list_renderer table.o_list_table th[data-name="price_subtotal"]',
            "position:sticky", "min-width:6.5rem",
        )
