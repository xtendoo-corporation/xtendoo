from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import PortalCommon


@tagged("post_install", "-at_install")
class TestPortalAccess(PortalCommon):
    def test_tokens_are_stored_hashed(self):
        access, token = self.Access._create_pending(self.employee)
        self.assertNotEqual(access.activation_hash, token)
        self.assertEqual(len(access.activation_hash), 64)
        self.assertGreaterEqual(len(token), 40)  # >= 256 bits urlsafe

    def test_redeem_is_single_use(self):
        access, token = self.Access._create_pending(self.employee)
        redeemed, session = self.Access._redeem(token)
        self.assertEqual(redeemed, access)
        self.assertEqual(access.state, "active")
        again, _ = self.Access._redeem(token)  # a bound link can't be reused
        self.assertFalse(again)

    def test_redeem_rejects_wrong_and_malformed_tokens(self):
        self.Access._create_pending(self.employee)
        for bad in (None, "", "nope", "x" * 500):
            access, session = self.Access._redeem(bad)
            self.assertFalse(access)
            self.assertFalse(session)

    def test_activation_link_expires(self):
        access, token = self.Access._create_pending(self.employee)
        access.activation_expires = fields.Datetime.now() - timedelta(minutes=1)
        self.assertFalse(self.Access._redeem(token)[0])

    def test_session_resolves_employee(self):
        access, session = self._activate()
        self.assertEqual(self.Access._resolve_session(session).employee_id, self.employee)
        self.assertFalse(self.Access._resolve_session("garbage"))
        self.assertFalse(self.Access._resolve_session(False))

    def test_session_expires(self):
        access, session = self._activate()
        access.session_expires = fields.Datetime.now() - timedelta(seconds=1)
        self.assertFalse(self.Access._resolve_session(session))

    def test_revocation(self):
        access, session = self._activate()
        self.employee.action_portal_revoke_all()
        self.assertEqual(access.state, "revoked")
        self.assertFalse(self.Access._resolve_session(session))

    def test_archived_employee_or_disabled_company_loses_access(self):
        access, session = self._activate()
        self.company.portal_attendance_enabled = False
        self.assertFalse(self.Access._resolve_session(session))
        self.company.portal_attendance_enabled = True
        self.assertTrue(self.Access._resolve_session(session))
        self.employee.active = False
        self.assertFalse(self.Access._resolve_session(session))

    def test_throttle_blocks_after_failures(self):
        Attempt = self.env["hr.attendance.portal.attempt"]
        Attempt.search([]).unlink()
        ip = "203.0.113.9"
        self.assertFalse(Attempt._is_blocked(ip))
        for _i in range(5):
            Attempt._register_failure(ip)
        self.assertTrue(Attempt._is_blocked(ip))
        self.assertFalse(Attempt._is_blocked("203.0.113.10"))
        self.assertNotIn(ip, Attempt.search([]).mapped("ip_hash"))

    def test_unlink_device_frees_the_same_link(self):
        access, token = self.Access._create_pending(self.employee)
        _a, session = self.Access._redeem(token)
        self.assertFalse(self.Access._redeem(token)[0])
        access.action_unlink_device()
        self.assertEqual(access.state, "pending")
        self.assertFalse(self.Access._resolve_session(session))
        self.assertFalse(access.device_info)
        again, new_session = self.Access._redeem(token)  # same link, new device
        self.assertEqual(again, access)
        self.assertNotEqual(new_session, session)
        self.assertTrue(self.Access._resolve_session(new_session))
        self.assertFalse(self.Access._resolve_session(session))

    def test_unlink_does_not_resurrect_revoked_or_expire_rules(self):
        access, token = self.Access._create_pending(self.employee)
        self.Access._redeem(token)
        access.action_revoke()
        access.action_unlink_device()
        self.assertEqual(access.state, "revoked")
        self.assertFalse(self.Access._redeem(token)[0])

    def test_renew_replaces_the_access(self):
        access, token = self.Access._create_pending(self.employee)
        _a, session = self.Access._redeem(token)
        action = access.action_renew()
        self.assertEqual(action["tag"], "display_notification")
        self.assertIn("/fichaje/activar/", action["params"]["message"])
        self.assertEqual(access.state, "revoked")
        self.assertFalse(self.Access._redeem(token)[0])  # old link is dead
        self.assertFalse(self.Access._resolve_session(session))
        pending = self.employee.portal_access_ids.filtered(lambda a: a.state == "pending")
        self.assertEqual(len(pending), 1)
