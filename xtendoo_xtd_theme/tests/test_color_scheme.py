# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, new_test_user, tagged
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
        cls.user = new_test_user(
            cls.env, login="xtd_scheme_user", password="xtd_scheme_user", groups="base.group_user"
        )

    def _open(self, preference, path="/odoo"):
        self.user.color_scheme = preference
        self.authenticate(self.user.login, "xtd_scheme_user")
        return self.url_open(path)

    def test_internal_user_dark_cookie_is_set(self):
        self.assertEqual(self._open("dark").cookies.get("color_scheme"), "dark")

    def test_internal_user_light_cookie_is_set(self):
        self.assertEqual(self._open("light").cookies.get("color_scheme"), "light")

    def test_html_pages_carry_the_scheme_headers(self):
        response = self._open("dark")

        self.assertIn("Sec-CH-Prefers-Color-Scheme", response.headers.get("Vary", ""))
        self.assertIn("Sec-CH-Prefers-Color-Scheme", response.headers.get("Accept-CH", ""))

    def test_non_html_responses_skip_scheme_work(self):
        """Imágenes, RPC y assets no tienen tema: sin cookie ni cabeceras (que
        además empeoraban la caché de esos ficheros)."""
        response = self._open("dark", f"/web/image/res.users/{self.user.id}/avatar_128")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("text/html", response.headers.get("Content-Type", ""))
        self.assertNotIn("color_scheme", response.cookies)
        self.assertNotIn("Sec-CH-Prefers-Color-Scheme", response.headers.get("Vary", ""))
        self.assertNotIn("Accept-CH", response.headers)

    def test_head_script_only_runs_with_system_preference(self):
        """Con "Sistema" el tema se corrige en un script de cabecera, antes de
        descargar los bundles; con una preferencia fija no hace falta."""
        system = self._open("system").text
        fixed = self._open("dark").text

        self.assertIn('data-preference="system"', system)
        self.assertIn("xtd_scheme_reload", system)
        self.assertIn('data-preference="dark"', fixed)
        self.assertLess(
            system.index("xtd_scheme_reload"),
            system.index("web.assets_web"),
            "El script debe ir antes de los bundles",
        )

    def test_portal_user_is_never_given_a_dark_scheme(self):
        portal = new_test_user(
            self.env, login="xtd_scheme_portal", password="xtd_scheme_portal", groups="base.group_portal"
        )
        self.authenticate(portal.login, "xtd_scheme_portal")

        self.assertNotEqual(self.url_open("/my").cookies.get("color_scheme"), "dark")
