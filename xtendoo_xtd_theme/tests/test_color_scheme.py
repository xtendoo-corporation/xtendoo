# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


class TestXtdThemeColorScheme(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref("base.user_admin").sudo()

    def test_user_color_scheme_related_field(self):
        self.user.write({"color_scheme": "system"})

        self.assertEqual(self.user.color_scheme, "system")
        self.user.color_scheme = "dark"
        self.assertEqual(self.user.res_users_settings_id.color_scheme, "dark")
        self.assertEqual(self.user.color_scheme, "dark")

    def test_user_can_write_own_color_scheme(self):
        self.user.write({"color_scheme": "light"})
        self.assertEqual(self.user.res_users_settings_id.color_scheme, "light")

    def test_sidebar_app_order_is_stored_in_user_settings(self):
        settings = self.user.res_users_settings_id
        order = [42, 7, 13]

        formatted = settings.set_res_users_settings({"xtd_sidebar_app_order": order})

        self.assertEqual(settings.xtd_sidebar_app_order, order)
        self.assertEqual(formatted["xtd_sidebar_app_order"], order)


@tagged("post_install", "-at_install")
class TestXtdThemeColorSchemeHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].sudo().search(
            [("login", "=", "xtendoo")],
            limit=1,
        )
        cls.user.write({"password": "xtendoo"})

    def test_internal_user_dark_cookie_is_set(self):
        self.user.write({"color_scheme": "dark"})

        self.authenticate(self.user.login, "xtendoo")
        response = self.url_open("/odoo")

        self.assertEqual(response.cookies.get("color_scheme"), "dark")

    def test_internal_user_light_cookie_is_set(self):
        self.user.write({"color_scheme": "light"})

        self.authenticate(self.user.login, "xtendoo")
        response = self.url_open("/odoo")

        self.assertEqual(response.cookies.get("color_scheme"), "light")






