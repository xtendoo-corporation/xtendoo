# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDashboardGraphAssets(TransactionCase):
    """El parche de los gráficos de tablero viaja en el bundle del backend."""

    def test_graph_patch_is_in_backend_bundle(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_backend", css=False, js=True)
        paths = [asset.url for asset in bundle.javascripts]
        self.assertIn(
            "/xtendoo_xtd_theme/static/src/js/xtd_dashboard_graph.esm.js", paths
        )
