from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import PortalCommon

GOOD = dict(geo_status="ok", latitude="37.3891", longitude="-5.9845", accuracy="20")


@tagged("post_install", "-at_install")
class TestPortalPunch(PortalCommon):
    def _in(self, employee=None, **geo):
        return self.Punch.punch(employee or self.employee, "check_in", **(geo or GOOD))

    def _age(self, attendance, days):
        """Move a finished punch into the past: standard Odoo orders the
        'last attendance' by check_in with 1 s resolution, so two punches in
        the same second would tie (impossible with real people)."""
        attendance.write(
            {
                "check_in": attendance.check_in - timedelta(days=days),
                "check_out": attendance.check_out - timedelta(days=days),
            }
        )

    def test_check_in_and_out_use_standard_model(self):
        att = self._in()
        self.assertEqual(att._name, "hr.attendance")
        self.assertEqual(att.employee_id, self.employee)
        self.assertEqual(att.in_mode, "mobile_portal")
        self.assertEqual(att.in_location_status, "ok")
        self.assertAlmostEqual(att.in_latitude, 37.3891, places=4)
        self.assertEqual(att.in_accuracy, 20.0)
        out = self.Punch.punch(self.employee, "check_out", **GOOD)
        self.assertEqual(out, att)
        self.assertTrue(att.check_out)
        self.assertEqual(att.out_mode, "mobile_portal")

    def test_server_time_is_used(self):
        att = self._in()
        self.assertTrue(att.check_in)  # no client timestamp is accepted at all

    def test_inconsistent_actions_are_rejected(self):
        with self.assertRaises(UserError):  # check out while out
            self.Punch.punch(self.employee, "check_out", **GOOD)
        self._in()
        with self.assertRaises(UserError):  # double check in (double tap)
            self._in()
        self.assertEqual(
            self.env["hr.attendance"].search_count([("employee_id", "=", self.employee.id)]), 1
        )

    def test_invalid_action(self):
        with self.assertRaises(UserError):
            self.Punch.punch(self.employee, "toggle", **GOOD)

    def test_invalid_location_data_rejected(self):
        bad = [
            dict(latitude="91", longitude="0.5", accuracy="5"),
            dict(latitude="10", longitude="181", accuracy="5"),
            dict(latitude="abc", longitude="1", accuracy="5"),
            dict(latitude="nan", longitude="1", accuracy="5"),
            dict(latitude="inf", longitude="1", accuracy="5"),
            dict(latitude="10", longitude="1", accuracy="-3"),
            dict(latitude="0", longitude="0", accuracy="5"),
            dict(latitude=None, longitude=None, accuracy=None),
        ]
        for vals in bad:
            with self.assertRaises(UserError, msg=str(vals)):
                self.Punch.punch(self.employee, "check_in", geo_status="ok", **vals)
        with self.assertRaises(UserError):
            self.Punch.punch(self.employee, "check_in", geo_status="whatever")
        self.assertFalse(self.employee.attendance_state == "checked_in")

    def test_denied_permission_still_punches_flagged_without_coordinates(self):
        att = self.Punch.punch(
            self.employee, "check_in", geo_status="denied",
            latitude="37.1", longitude="-5.1", accuracy="5",  # must be ignored
        )
        self.assertEqual(att.in_location_status, "denied")
        self.assertFalse(att.in_latitude)
        self.assertFalse(att.in_longitude)
        self.assertFalse(att.in_accuracy)

    def test_declined_by_employee_is_flagged_and_stores_no_location(self):
        att = self.Punch.punch(
            self.employee, "check_in", geo_status="declined",
            latitude="37.1", longitude="-5.1", accuracy="5",
        )
        self.assertEqual(att.in_location_status, "declined")
        self.assertFalse(att.in_latitude)
        self.company.portal_attendance_location_policy = "required"
        with self.assertRaises(UserError):
            self.Punch.punch(self.other, "check_in", geo_status="declined")

    def test_gps_failures_are_flagged(self):
        for status, expected in (("unavailable", "unavailable"), ("timeout", "unavailable"),
                                 ("unsupported", "unavailable")):
            att = self.Punch.punch(self.other, "check_in", geo_status=status)
            self.assertEqual(att.in_location_status, expected)
            self._age(self.Punch.punch(self.other, "check_out", geo_status="denied"), 5)

    def test_low_accuracy_is_flagged_but_kept(self):
        att = self.Punch.punch(
            self.employee, "check_in", geo_status="ok",
            latitude="37.3", longitude="-5.9", accuracy="500",
        )
        self.assertEqual(att.in_location_status, "low_accuracy")
        self.assertEqual(att.in_accuracy, 500.0)

    def test_required_policy_rejects_missing_or_imprecise_location(self):
        self.company.portal_attendance_location_policy = "required"
        with self.assertRaises(UserError):
            self.Punch.punch(self.employee, "check_in", geo_status="denied")
        with self.assertRaises(UserError):
            self.Punch.punch(self.employee, "check_in", geo_status="ok",
                             latitude="37.3", longitude="-5.9", accuracy="500")
        self.assertTrue(self._in())

    def test_device_tracking_setting_controls_ip_and_browser(self):
        self.company.attendance_device_tracking = False
        att = self.Punch.punch(self.employee, "check_in", ip_address="1.2.3.4",
                               browser="firefox", **GOOD)
        self.assertFalse(att.in_ip_address)
        self.Punch.punch(self.employee, "check_out", **GOOD)
        self.company.attendance_device_tracking = True
        att = self.Punch.punch(self.employee, "check_in", ip_address="1.2.3.4",
                               browser="firefox", **GOOD)
        self.assertEqual(att.in_ip_address, "1.2.3.4")

    def test_history_only_contains_own_records_and_is_paginated(self):
        for i in range(3):
            self._in()
            self._age(self.Punch.punch(self.employee, "check_out", **GOOD), i + 1)
        self.Punch.punch(self.other, "check_in", **GOOD)
        mine = self.Punch.get_history(self.employee, page=1, page_size=2)
        self.assertEqual(mine["total"], 3)
        self.assertEqual(mine["pages"], 2)
        self.assertEqual(len(mine["rows"]), 2)
        theirs = self.Punch.get_history(self.other)
        self.assertEqual(theirs["total"], 1)
        self.assertTrue(theirs["rows"][0]["open"])
        # out-of-range pages are clamped
        self.assertEqual(self.Punch.get_history(self.employee, page=99, page_size=2)["page"], 2)
