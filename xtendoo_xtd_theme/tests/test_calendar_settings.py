# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestXtdCalendarSettings(TransactionCase):
    def setUp(self):
        super().setUp()
        self.settings = self.env.ref("base.user_admin").sudo().res_users_settings_id

    def test_default_range_is_the_whole_day(self):
        defaults = self.env["res.users.settings"].default_get(
            ["xtd_calendar_hour_start", "xtd_calendar_hour_end"]
        )
        self.assertEqual(defaults, {"xtd_calendar_hour_start": 0, "xtd_calendar_hour_end": 24})

    def test_user_can_set_a_valid_range(self):
        self.settings.write({"xtd_calendar_hour_start": 7, "xtd_calendar_hour_end": 21})
        user = self.settings.user_id
        self.assertEqual(user.xtd_calendar_hour_start, 7)
        self.assertEqual(user.xtd_calendar_hour_end, 21)

    def test_invalid_ranges_are_rejected(self):
        for start, end in ((10, 10), (12, 8), (-1, 8), (0, 25)):
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                self.settings.write({"xtd_calendar_hour_start": start, "xtd_calendar_hour_end": end})

    def test_range_is_exposed_to_the_web_client(self):
        self.settings.write({"xtd_calendar_hour_start": 8, "xtd_calendar_hour_end": 20})
        formatted = self.settings._res_users_settings_format()
        self.assertEqual(formatted["xtd_calendar_hour_start"], 8)
        self.assertEqual(formatted["xtd_calendar_hour_end"], 20)
