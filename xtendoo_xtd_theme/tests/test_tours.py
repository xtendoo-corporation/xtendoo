# -*- coding: utf-8 -*-

import unittest

import odoo.tests
from odoo.tests import new_test_user

LOGIN = "xtd_tour_admin"


@odoo.tests.tagged("post_install", "-at_install")
class TestXtdThemeTours(odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "calendar.event" not in cls.env:
            raise unittest.SkipTest("El tour recorre el calendario: se necesita el módulo calendar")
        # start_tour inicia sesión con login == contraseña.
        cls.user = new_test_user(
            cls.env, login=LOGIN, password=LOGIN, groups="base.group_user,base.group_system"
        )
        # El tour del calendario comprueba que se respeta la franja horaria del usuario.
        cls.user.res_users_settings_id.write({
            "xtd_calendar_hour_start": 9,
            "xtd_calendar_hour_end": 18,
        })

    def test_xtd_theme_backend_tour(self):
        self.start_tour(
            "/odoo/action-xtendoo_xtd_theme.action_xtd_dashboard",
            "xtd_theme_backend_tour",
            login=LOGIN,
        )
