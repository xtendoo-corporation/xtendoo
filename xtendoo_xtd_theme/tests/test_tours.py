# -*- coding: utf-8 -*-

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestXtdThemeTours(odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].sudo().search(
            [("login", "=", "xtendoo")],
            limit=1,
        )
        cls.user.write({"password": "xtendoo"})

    def test_xtd_theme_backend_tour(self):
        self.start_tour("/odoo", "xtd_theme_backend_tour", login=self.user.login)







