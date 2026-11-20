# -*- coding: utf-8 -*-

import re

from odoo.tests import TransactionCase, tagged

MODULE = "xtendoo_xtd_theme"
PRIMARY_DARK = f"/{MODULE}/static/src/scss/variables/primary_variables.dark.scss"
BOOTSTRAP_DARK = f"/{MODULE}/static/src/scss/variables/bootstrap_overridden.dark.scss"
CORE_PRIMARY = "/web/static/src/scss/primary_variables.scss"
CORE_BOOTSTRAP = "/web/static/src/scss/bootstrap_overridden.scss"
# $o-gray-900 en claro (core) y en oscuro (variables/primary_variables.dark.scss)
LIGHT_GRAY_900 = "33, 37, 41"
DARK_GRAY_900 = "233, 229, 223"


@tagged("post_install", "-at_install")
class TestXtdDarkAssets(TransactionCase):
    """El modo oscuro se compila en oscuro, no es el CSS claro con parches.

    Odoo Community no trae variables oscuras: las aporta el tema y tienen que
    cargarse delante de las del core en los bundles oscuros (y solo en ellos).
    """

    def _bundle_urls(self, bundle_name):
        files, _external = self.env["ir.qweb"]._get_asset_content(bundle_name)
        return [asset["url"] for asset in files]

    def _assert_before(self, urls, first, second):
        self.assertIn(first, urls)
        self.assertIn(second, urls)
        self.assertLess(
            urls.index(first),
            urls.index(second),
            f"{first} debe cargarse antes que {second}",
        )

    def test_dark_variables_load_before_core_variables(self):
        for bundle_name in ("web.assets_web_dark", "web.assets_backend_lazy_dark"):
            with self.subTest(bundle=bundle_name):
                urls = self._bundle_urls(bundle_name)
                self._assert_before(urls, PRIMARY_DARK, CORE_PRIMARY)
                self._assert_before(urls, BOOTSTRAP_DARK, CORE_BOOTSTRAP)
                # Las variables primarias tienen que estar definidas cuando se
                # evalúan los ajustes de Bootstrap que dependen de ellas.
                self._assert_before(urls, CORE_PRIMARY, BOOTSTRAP_DARK)

    def test_light_bundles_do_not_get_dark_files(self):
        for bundle_name in ("web.assets_web", "web.assets_backend_lazy"):
            with self.subTest(bundle=bundle_name):
                dark_urls = [
                    url
                    for url in self._bundle_urls(bundle_name)
                    if url.startswith(f"/{MODULE}/") and ".dark." in url
                ]
                self.assertFalse(dark_urls)

    def test_dark_bundle_compiles_with_inverted_grays(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "web.assets_web_dark", css=True, js=False
        )
        attachments = bundle.css()

        self.assertFalse(bundle.css_errors, "\n".join(bundle.css_errors))
        css = "\n".join(
            attachment.raw.decode("utf-8") for attachment in attachments
        )
        self.assertNotIn("css_error_message", css)

        # .text-900 es el texto principal de medio Odoo (títulos de columna del
        # kanban, botones de estadísticas...): en oscuro tiene que ser claro.
        text_900 = re.search(r"\.text-900\s*\{[^}]*\}", css)
        self.assertTrue(text_900, "No se encontró la regla .text-900")
        self.assertIn(DARK_GRAY_900, text_900.group(0))
        self.assertNotIn(LIGHT_GRAY_900, text_900.group(0))

        # Etiquetas de colores con su variante oscura.
        self.assertIn(".o_tag.o_tag_color_1", css)
        self.assertRegex(css, r"color-scheme:\s*dark")
