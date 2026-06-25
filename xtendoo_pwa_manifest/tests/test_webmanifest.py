# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestXtendooPwaManifest(HttpCase):
    def test_webmanifest_overrides_odoo19_defaults(self):
        response = self.url_open("/web/manifest.webmanifest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/manifest+json")

        data = response.json()
        self.assertEqual(data["name"], "Odoo WhatsApp Chat")
        self.assertEqual(data["short_name"], "OdooChat")
        self.assertEqual(data["scope"], "/")
        self.assertEqual(data["start_url"], "/odoo")
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["background_color"], "#ffffff")
        self.assertEqual(data["theme_color"], "#075E54")
        self.assertFalse(data["prefer_related_applications"])

        self.assertIn("icons", data)
        self.assertIn("shortcuts", data)

    def test_webmanifest_uses_configured_values(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_pwa_manifest.name",
            "Configured App",
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "xtendoo_pwa_manifest.theme_color",
            "#123456",
        )

        response = self.url_open("/web/manifest.webmanifest")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Configured App")
        self.assertEqual(data["theme_color"], "#123456")
