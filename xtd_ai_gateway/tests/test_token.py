import os
import time
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from ..tools import token as token_lib
from ..tools.errors import XtdAiAuthError
from .common import SERVICE_KEY, XtdAiCase


@tagged("post_install", "-at_install")
class TestToken(XtdAiCase):
    def forge(self, user, run_rec, **overrides):
        """Sign a token with the real secret, overriding payload keys."""
        now = int(time.time())
        payload = {
            "v": 1,
            "db": self.env.cr.dbname,
            "uid": user.id,
            "conv": run_rec.conversation_id.id,
            "run": run_rec.id,
            "cids": [self.company.id],
            "lang": "en_US",
            "tz": "UTC",
            "iat": now,
            "exp": now + 600,
            "jti": run_rec.jti,
        }
        payload.update(overrides)
        return token_lib.build_token(self.env["xtd.ai.token"]._xtd_ai_secret(), payload)

    def assertAuthFails(self, token, status=401, code=-32001, reason=None, **kw):
        with self.assertRaises(XtdAiAuthError) as ctx:
            self.authenticate(token, **kw)
        self.assertEqual(ctx.exception.http_status, status)
        self.assertEqual(ctx.exception.rpc_code, code)
        if reason:
            self.assertEqual(ctx.exception.reason, reason)
        return ctx.exception

    def test_secret_generated_and_long(self):
        secret = self.env["xtd.ai.token"]._xtd_ai_secret()
        self.assertEqual(len(secret), 128)

    def test_valid_token(self):
        run, token = self.start_run()
        self.assertTrue(token.startswith("xtdai1."))
        payload = self.authenticate(token)
        self.assertEqual(payload["uid"], self.user.id)
        self.assertEqual(payload["run"], run.id)
        self.assertEqual(payload["conv"], run.conversation_id.id)
        self.assertEqual(payload["exp"] - payload["iat"], 600)
        self.assertEqual(payload["cids"][0], self.user.company_id.id)
        self.assertEqual(len(payload["jti"]), 32)
        self.assertEqual(payload["db"], self.env.cr.dbname)
        self.assertEqual(run.state, "queued")
        self.assertEqual(run.jti, payload["jti"])

    def test_tampered_signature_and_payload(self):
        run, token = self.start_run()
        prefix, payload, signature = token.split(".")
        flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
        self.assertAuthFails(f"{prefix}.{payload}.{flipped}", reason="bad_signature")
        other = self.forge(self.user2, run)  # valid for another uid
        _p, other_payload, _s = other.split(".")
        self.assertAuthFails(
            f"{prefix}.{other_payload}.{signature}", reason="bad_signature"
        )
        self.assertAuthFails("xtdai1.garbage", reason="malformed")
        self.assertAuthFails("other." + payload + "." + signature, reason="malformed")
        self.assertAuthFails("", reason="missing_token")

    def test_secret_rotation_invalidates(self):
        _run, token = self.start_run()
        self.env["xtd.ai.token"].with_user(self.manager)._xtd_ai_rotate_secret()
        self.assertAuthFails(token, reason="bad_signature")
        with self.assertRaises(AccessError):
            self.env["xtd.ai.token"].with_user(self.user)._xtd_ai_rotate_secret()

    def test_expired(self):
        run, _token = self.start_run()
        now = int(time.time())
        self.assertAuthFails(
            self.forge(self.user, run, iat=now - 700, exp=now - 100), reason="expired"
        )
        # within the 30 s tolerance
        self.authenticate(self.forge(self.user, run, iat=now - 620, exp=now - 20))

    def test_wrong_db(self):
        run, _token = self.start_run()
        self.assertAuthFails(
            self.forge(self.user, run, db="other_db"), reason="wrong_db"
        )
        _run, token = self.start_run(self.user2)
        self.assertAuthFails(token, reason="wrong_db", dbname="not_this_db")

    def test_inactive_user(self):
        _run, token = self.start_run()
        self.user.sudo().active = False
        self.assertAuthFails(token, reason="user_not_allowed")

    def test_user_loses_group(self):
        _run, token = self.start_run()
        self.user.sudo().group_ids = [
            (3, self.env.ref("xtd_ai_gateway.group_xtd_ai_user").id)
        ]
        self.assertAuthFails(token, reason="user_not_allowed")

    def test_user_without_ai_group_and_share_user(self):
        for user in (self.plain, self.portal):
            conversation = (
                self.env["xtd.ai.conversation"].sudo().create({"user_id": user.id})
            )
            run = (
                self.env["xtd.ai.run"]
                .sudo()
                .create(
                    {
                        "conversation_id": conversation.id,
                        "user_id": user.id,
                        "jti": "a" * 32,
                    }
                )
            )
            token = self.forge(user, run)
            self.assertAuthFails(token, reason="user_not_allowed")
        self.assertTrue(self.portal.share)

    def test_start_run_refuses_users_without_group(self):
        for user in (self.plain, self.portal):
            with self.assertRaises(AccessError):
                self.env["xtd.ai.conversation"].with_user(user)._xtd_ai_start_run(
                    "hola"
                )

    def test_run_mismatch(self):
        run, _token = self.start_run()
        run2, _token2 = self.start_run(self.user2)
        self.assertAuthFails(
            self.forge(self.user, run, uid=self.user2.id), reason="run_mismatch"
        )
        self.assertAuthFails(
            self.forge(self.user, run, conv=run2.conversation_id.id),
            reason="run_mismatch",
        )
        self.assertAuthFails(
            self.forge(self.user, run, jti="0" * 32), reason="run_mismatch"
        )
        self.assertAuthFails(
            self.forge(self.user, run, run=run2.id), reason="run_mismatch"
        )
        self.assertAuthFails(
            self.forge(self.user, run, run=999999999), reason="run_mismatch"
        )

    def test_run_finished_or_cancelled(self):
        for state in ("done", "failed", "cancelled"):
            user = self.user2
            run, token = self.start_run(user)
            run.state = state
            self.assertAuthFails(
                token, status=409, code=-32004, reason="run_not_active"
            )
            run.conversation_id.state = "closed"  # allow a fresh conversation next loop
        run, token = self.start_run(self.user)
        run.state = "running"
        self.authenticate(token)  # running is fine

    def test_conversation_closed(self):
        run, token = self.start_run()
        run.conversation_id.state = "closed"
        self.assertAuthFails(token, reason="conversation_closed")

    def test_companies_not_allowed(self):
        run, _token = self.start_run()
        exc = self.assertAuthFails(
            self.forge(self.user, run, cids=[self.company.id, self.company2.id]),
            status=403,
            code=-32003,
            reason="company_not_allowed",
        )
        self.assertEqual(exc.user_id, self.user.id)

    def test_service_key(self):
        _run, token = self.start_run()
        self.assertAuthFails(token, key=None, reason="bad_service_key")
        self.assertAuthFails(token, key="wrong", reason="bad_service_key")
        self.assertAuthFails(token, key=SERVICE_KEY + "x", reason="bad_service_key")
        with patch.dict(os.environ):
            os.environ.pop("XTD_AI_SERVICE_KEY")
            self.assertAuthFails(
                token, status=503, code=-32010, reason="service_key_unset"
            )
        with patch.dict(os.environ, {"XTD_AI_SERVICE_KEY": ""}):
            self.assertAuthFails(
                token, status=503, code=-32010, reason="service_key_unset"
            )

    def test_missing_bearer(self):
        env_su = self.env(user=1, su=True)
        with self.assertRaises(XtdAiAuthError) as ctx:
            env_su["xtd.ai.token"]._xtd_ai_authenticate(
                {"X-XTD-AI-Service-Key": SERVICE_KEY}, self.env.cr.dbname
            )
        self.assertEqual(ctx.exception.http_status, 401)

    def test_one_active_run_per_conversation(self):
        self.start_run()
        with self.assertRaises(UserError):
            self.start_run()

    def test_stale_run_does_not_block(self):
        run, _token = self.start_run()
        self.env.cr.execute(
            "UPDATE xtd_ai_run SET create_date = now() - interval '2 hours' WHERE id "
            "= %s",
            (run.id,),
        )
        run.invalidate_recordset()
        run2, _token2 = self.start_run()
        self.assertEqual(run.state, "failed")
        self.assertNotEqual(run2.id, run.id)
