import json

import werkzeug.wrappers
from werkzeug.exceptions import HTTPException

from odoo import SUPERUSER_ID, api, models
from odoo.http import request

from ..tools.errors import XtdAiAuthError


class XtdAiHttpError(HTTPException):
    """HTTP error with a JSON-RPC 2.0 body (returned as is by Odoo's dispatcher)."""

    def __init__(self, http_status, rpc_code, message):
        super().__init__(description=message)
        self.code = http_status
        self.rpc_code = rpc_code

    def get_response(self, environ=None, scope=None):
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": self.rpc_code, "message": self.description},
            }
        )
        return werkzeug.wrappers.Response(
            body,
            status=self.code,
            content_type="application/json",
            headers=[("Cache-Control", "no-store")],
        )


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_xtd_ai(cls):
        """Authentication of the AI service routes (CONTRACT §3).

        Requires the service key and a valid execution token; ignores session
        cookies. The environment becomes the token's user, never superuser.
        """
        env_su = api.Environment(request.env.cr, SUPERUSER_ID, {})
        try:
            payload = env_su["xtd.ai.token"]._xtd_ai_authenticate(
                request.httprequest.headers, request.env.cr.dbname
            )
        except XtdAiAuthError as exc:
            if exc.http_status != 503:
                env_su["xtd.ai.audit"]._xtd_ai_log_auth_failed(
                    request.env.registry, exc.reason, exc.user_id, exc.run_id
                )
            raise XtdAiHttpError(exc.http_status, exc.rpc_code, exc.message) from None
        request.update_env(
            user=payload["uid"],
            context={
                "allowed_company_ids": payload["cids"],
                "lang": payload["lang"],
                "tz": payload["tz"],
                "xtd_ai_run": payload["run"],
                "mail_auto_subscribe_no_notify": True,
                "mail_notify_force_send": False,
            },
        )
        request.session.can_save = False  # stateless
