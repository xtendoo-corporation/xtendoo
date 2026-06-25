# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers import webmanifest


class WebManifest(webmanifest.WebManifest):
    def _get_param(self, key, default):
        return request.env["ir.config_parameter"].sudo().get_param(key, default)

    def _get_pwa_values(self):
        return {
            "name": self._get_param("xtendoo_pwa_manifest.name", "Odoo WhatsApp Chat"),
            "short_name": self._get_param(
                "xtendoo_pwa_manifest.short_name", "OdooChat"
            ),
            "scope": self._get_param("xtendoo_pwa_manifest.scope", "/"),
            "start_url": self._get_param(
                "xtendoo_pwa_manifest.start_url", "/odoo"
            ),
            "display": self._get_param("xtendoo_pwa_manifest.display", "standalone"),
            "background_color": self._get_param(
                "xtendoo_pwa_manifest.background_color", "#ffffff"
            ),
            "theme_color": self._get_param(
                "xtendoo_pwa_manifest.theme_color", "#075E54"
            ),
            "prefer_related_applications": False,
        }

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        manifest.update(self._get_pwa_values())
        return manifest

    @http.route(
        "/web/manifest.webmanifest",
        type="http",
        auth="public",
        methods=["GET"],
        readonly=True,
    )
    def webmanifest(self):
        return request.make_json_response(
            self._get_webmanifest(),
            {"Content-Type": "application/manifest+json"},
        )
