# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestXtdThemeBrandingHttp(HttpCase):
    def test_database_manager_is_xtd_branded(self):
        response = self.url_open("/web/database/manager")

        self.assertEqual(response.status_code, 200)
        self.assertIn("<title>Xtd</title>", response.text)
        self.assertIn("xtd_logo_negative.svg", response.text)
        self.assertNotIn("<title>Odoo</title>", response.text)
        self.assertNotIn("logo2.png", response.text)
        self.assertNotIn("Odoo database manager", response.text)

