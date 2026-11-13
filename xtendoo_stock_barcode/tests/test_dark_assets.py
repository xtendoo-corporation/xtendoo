# -*- coding: utf-8 -*-

from pathlib import Path

from odoo.modules.module import get_manifest
from odoo.tests import TransactionCase, tagged

MODULE = "xtendoo_stock_barcode"
DARK_SCSS = f"{MODULE}/static/src/scss/stock_barcode.dark.scss"


@tagged("post_install", "-at_install")
class TestStockBarcodeDarkAssets(TransactionCase):
    """La hoja clara fija negro y blanco con !important: en modo oscuro hace
    falta una hoja propia, cargada solo en el bundle oscuro."""

    def test_dark_stylesheet_is_only_in_dark_bundle(self):
        assets = get_manifest(MODULE)["assets"]

        self.assertIn(DARK_SCSS, assets["web.assets_web_dark"])
        self.assertNotIn(DARK_SCSS, assets["web.assets_backend"])

        qweb = self.env["ir.qweb"]
        dark_urls = [a["url"] for a in qweb._get_asset_content("web.assets_web_dark")[0]]
        light_urls = [a["url"] for a in qweb._get_asset_content("web.assets_web")[0]]
        self.assertIn(f"/{DARK_SCSS}", dark_urls)
        self.assertNotIn(f"/{DARK_SCSS}", light_urls)

    def test_dark_stylesheet_overrides_hardcoded_light_colours(self):
        content = (Path(__file__).resolve().parents[1] / "static/src/scss/stock_barcode.dark.scss").read_text(
            encoding="utf-8"
        )

        for selector in (".btn-primary,", ".btn-outline-primary {", ".card-header {", ".list-group-item {", ".text-primary,"):
            self.assertIn(selector, content)
        # Funciona con y sin el tema Xtd: tokens del tema con valor de reserva.
        self.assertIn("var(--xtd-surface, #232220)", content)
