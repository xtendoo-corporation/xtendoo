import hmac
import os
import re
import secrets
import time

from odoo import api, models
from odoo.exceptions import AccessError

from ..tools import token as token_lib
from ..tools.errors import XtdAiAuthError

SECRET_PARAM = "xtd_ai_gateway.token_secret"
SERVICE_KEY_ENV = "XTD_AI_SERVICE_KEY"


class XtdAiToken(models.AbstractModel):
    """Token minting and verification (CONTRACT §2, §3). Not exposed through RPC."""

    _name = "xtd.ai.token"
    _description = "AI agent token service"

    # ------------------------------------------------------------------
    # Secret
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_secret(self):
        # sudo: the secret parameter is only readable by the system group.
        return self.env["ir.config_parameter"].sudo().get_param(SECRET_PARAM) or ""

    @api.model
    def _xtd_ai_ensure_secret(self):
        icp = self.env["ir.config_parameter"].sudo()  # sudo: system parameter
        if not icp.get_param(SECRET_PARAM):
            icp.set_param(SECRET_PARAM, secrets.token_hex(64))

    @api.model
    def _xtd_ai_rotate_secret(self):
        """Replace the signing secret: every token in flight becomes invalid."""
        if not self.env.su and not self.env.user.has_group(
            "xtd_ai_gateway.group_xtd_ai_manager"
        ):
            raise AccessError(
                self.env._("Solo el administrador del agente IA puede hacerlo.")
            )
        # sudo: system parameter, caller checked above
        self.env["ir.config_parameter"].sudo().set_param(
            SECRET_PARAM, secrets.token_hex(64)
        )

    @api.model
    def _xtd_ai_new_jti(self):
        return secrets.token_hex(16)

    @api.model
    def _xtd_ai_service_key(self):
        return os.environ.get(SERVICE_KEY_ENV, "")

    # ------------------------------------------------------------------
    # Minting
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_mint(self, user, conversation, run, cids, jti):
        self._xtd_ai_ensure_secret()
        now = int(time.time())
        payload = {
            "v": 1,
            "db": self.env.cr.dbname,
            "uid": user.id,
            "conv": conversation.id,
            "run": run.id,
            "cids": [int(c) for c in cids],
            "lang": user.lang or "en_US",
            "tz": user.tz or "UTC",
            "iat": now,
            "exp": now + token_lib.TTL,
            "jti": jti,
        }
        return token_lib.build_token(self._xtd_ai_secret(), payload)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_check_service_key(self, headers):
        expected = self._xtd_ai_service_key()
        if not expected:
            raise XtdAiAuthError(
                503, -32010, "AI gateway not configured", reason="service_key_unset"
            )
        given = headers.get("X-XTD-AI-Service-Key") or ""
        if not hmac.compare_digest(given.encode(), expected.encode()):
            raise XtdAiAuthError(
                401, -32001, "Invalid credentials", reason="bad_service_key"
            )

    @api.model
    def _xtd_ai_authenticate(self, headers, dbname):
        """Validate service key + bearer token (CONTRACT §2 order).

        Must be called with a superuser environment (it reads users and runs).
        :returns: the verified payload.
        :raises: ``XtdAiAuthError``.
        """
        self._xtd_ai_check_service_key(headers)
        header = headers.get("Authorization") or ""
        match = re.match(r"^bearer\s+(\S+)$", header, re.IGNORECASE)
        if not match:
            raise XtdAiAuthError(
                401, -32001, "Invalid credentials", reason="missing_token"
            )
        secret = self._xtd_ai_secret()
        if not secret:
            raise XtdAiAuthError(401, -32001, "Invalid credentials", reason="no_secret")
        payload, reason = token_lib.parse_token(secret, match.group(1))
        if payload is None:
            raise XtdAiAuthError(401, -32001, "Invalid credentials", reason=reason)
        uid, run_id = payload["uid"], payload["run"]

        def fail(reason, http_status=401, code=-32001, message="Invalid credentials"):
            user = self.env["res.users"].browse(uid).exists()
            run = self.env["xtd.ai.run"].browse(run_id).exists()
            raise XtdAiAuthError(
                http_status,
                code,
                message,
                reason=reason,
                user_id=user.id if user else None,
                run_id=run.id if run else None,
            )

        if payload["db"] != dbname:
            fail("wrong_db")
        user = self.env["res.users"].browse(uid).exists()
        if not (
            user
            and user.active
            and not user.share
            and user._has_group("xtd_ai_gateway.group_xtd_ai_user")
        ):
            fail("user_not_allowed")
        run = self.env["xtd.ai.run"].browse(run_id).exists()
        if (
            not run
            or run.user_id.id != uid
            or run.conversation_id.id != payload["conv"]
            or not hmac.compare_digest(
                (run.jti or "").encode(), payload["jti"].encode()
            )
        ):
            fail("run_mismatch")
        if run.state not in ("queued", "running"):
            fail("run_not_active", 409, -32004, "Run is not active")
        conversation = run.conversation_id
        if conversation.state != "open" or conversation.user_id.id != uid:
            fail("conversation_closed")
        if not set(payload["cids"]) <= set(user.company_ids.ids):
            fail("company_not_allowed", 403, -32003, "Company not allowed")
        return payload
