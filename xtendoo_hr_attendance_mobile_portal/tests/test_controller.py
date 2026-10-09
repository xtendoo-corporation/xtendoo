import re

from odoo.tests import HttpCase, tagged

from .common import PortalCommon

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"|data-csrf="([^"]+)"')
GEO = {"geo_status": "ok", "latitude": "37.3891", "longitude": "-5.9845", "accuracy": "15"}


@tagged("post_install", "-at_install")
class TestPortalHttp(HttpCase, PortalCommon):
    def _fresh_session(self):
        # Drop only our cookie: HttpCase's own session cookie carries the db.
        for cookie in list(self.opener.cookies):
            if cookie.name == "xtd_hr_mp":
                self.opener.cookies.clear(cookie.domain, cookie.path, cookie.name)

    def _csrf(self, url="/fichaje/activar/x"):
        res = self.url_open(url)
        match = CSRF_RE.search(res.text)
        self.assertTrue(match, "CSRF token missing in page")
        return match.group(1) or match.group(2)

    def _login(self, employee):
        """Activate through the real HTTP flow; leaves cookies in self.opener."""
        self._fresh_session()
        access, token = self.Access._create_pending(employee)
        self.env.flush_all()
        csrf = self._csrf(f"/fichaje/activar/{token}")
        res = self.url_open("/fichaje/activar", data={"token": token, "csrf_token": csrf})
        self.assertEqual(res.status_code, 200)
        return access, token

    def test_activation_get_does_not_consume_token(self):
        self._fresh_session()
        access, token = self.Access._create_pending(self.employee)
        self.env.flush_all()
        res = self.url_open(f"/fichaje/activar/{token}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(access.state, "pending")

    def test_activation_flow_and_home(self):
        access, token = self._login(self.employee)
        self.assertEqual(access.state, "active")
        cookie = next(c for c in self.opener.cookies if c.name == "xtd_hr_mp")
        self.assertTrue(cookie.has_nonstandard_attr("HttpOnly"))
        home = self.url_open("/fichaje")
        self.assertEqual(home.status_code, 200)
        self.assertIn("Ana Portal", home.text)
        self.assertIn("no-store", home.headers["Cache-Control"])
        self.assertNotIn("Beto Portal", home.text)
        # reusing the link fails
        csrf = self._csrf()
        res = self.url_open("/fichaje/activar", data={"token": token, "csrf_token": csrf})
        self.assertEqual(res.status_code, 400)

    def test_no_session_is_rejected(self):
        self._fresh_session()
        self.assertEqual(self.url_open("/fichaje").status_code, 401)
        self.assertEqual(self.url_open("/fichaje/historial").status_code, 401)

    def test_activation_throttling(self):
        self.env["hr.attendance.portal.attempt"].search([]).unlink()
        self._fresh_session()
        csrf = self._csrf()
        codes = [
            self.url_open("/fichaje/activar", data={"token": "bad%d" % i, "csrf_token": csrf}).status_code
            for i in range(7)
        ]
        self.assertEqual(codes[:5], [400] * 5)
        self.assertEqual(codes[5:], [429] * 2)

    def test_punch_requires_csrf(self):
        self._login(self.employee)
        res = self.url_open("/fichaje/marcar", data={"action": "check_in", **GEO})
        self.assertNotEqual(res.status_code, 200)
        self.assertFalse(self.employee.attendance_state == "checked_in")

    def test_punch_in_out_through_http(self):
        self._login(self.employee)
        csrf = self._csrf("/fichaje")  # the home page exposes it in data-csrf
        res = self.url_open("/fichaje/marcar", data={"csrf_token": csrf, "action": "check_in", **GEO})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()["checked_in"])
        att = self.env["hr.attendance"].search([("employee_id", "=", self.employee.id)])
        self.assertEqual(len(att), 1)
        self.assertEqual(att.in_mode, "mobile_portal")
        # same action twice -> rejected, nothing flips
        res = self.url_open("/fichaje/marcar", data={"csrf_token": csrf, "action": "check_in", **GEO})
        self.assertEqual(res.status_code, 400)
        res = self.url_open("/fichaje/marcar", data={"csrf_token": csrf, "action": "check_out",
                                                    "geo_status": "denied"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["geo"])
        self.assertEqual(att.out_location_status, "denied")

    def test_employee_cannot_be_chosen_by_request(self):
        self._login(self.employee)
        csrf = self._csrf("/fichaje")
        self.url_open("/fichaje/marcar", data={
            "csrf_token": csrf, "action": "check_in", "employee_id": self.other.id,
            "employee": self.other.id, **GEO})
        self.assertEqual(self.employee.attendance_state, "checked_in")
        self.assertEqual(self.other.attendance_state, "checked_out")

    def test_history_is_isolated_between_employees(self):
        self.Punch.punch(self.other, "check_in", **GEO)
        self.env["hr.attendance"].search([("employee_id", "=", self.other.id)]).write(
            {"check_in": "2020-01-02 08:00:00", "check_out": "2020-01-02 16:00:00"})
        self.Punch.punch(self.employee, "check_in", **GEO)
        self._login(self.employee)
        res = self.url_open("/fichaje/historial")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("02/01/2020", res.text)
        self.assertNotIn("Beto", res.text)
        res = self.url_open("/fichaje/historial?page=abc&employee_id=%s" % self.other.id)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("02/01/2020", res.text)

    def test_revoked_session_cannot_punch(self):
        access, _token = self._login(self.employee)
        csrf = self._csrf("/fichaje")
        self.employee.action_portal_revoke_all()
        self.env.flush_all()
        res = self.url_open("/fichaje/marcar", data={"csrf_token": csrf, "action": "check_in", **GEO})
        self.assertEqual(res.status_code, 401)
        self.assertEqual(self.employee.attendance_state, "checked_out")

    def test_assets_are_cache_busted(self):
        self._fresh_session()
        html = self.url_open("/fichaje/activar/x").text
        match = re.search(r'portal\.css\?v=([0-9a-f]{10})', html)
        self.assertTrue(match, "stylesheet URL must carry a content version")
        self.assertIn("portal.js?v=" + match.group(1), html)
        res = self.url_open("/xtendoo_hr_attendance_mobile_portal/static/src/css/portal.css?v=" + match.group(1))
        self.assertEqual(res.status_code, 200)

    def test_manifest_and_icons(self):
        res = self.url_open("/fichaje/manifest.webmanifest")
        self.assertEqual(res.status_code, 200)
        self.assertIn("manifest+json", res.headers["Content-Type"])
        data = res.json()
        self.assertEqual(data["display"], "standalone")
        for icon in data["icons"]:
            self.assertEqual(self.url_open(icon["src"]).status_code, 200)
