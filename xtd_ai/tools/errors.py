from odoo.exceptions import UserError


class XtdAiDraftOnlyError(UserError):
    """Raised by the "draft only" guards when an AI run tries a forbidden action.

    The gateway maps it to the tool error code ``draft_only`` and audits it as
    ``guard_blocked``.
    """

    code = "draft_only"


class XtdAiToolError(Exception):
    """Controlled error raised by a tool (or a helper) with a stable code.

    ``code`` is one of the codes of CONTRACT §4.1 (``not_found``, ``ambiguous``,
    ``validation``...). ``data`` is optional structured information for the LLM
    (e.g. ``{"candidates": [...]}``).
    """

    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class XtdAiRpcError(Exception):
    """JSON-RPC protocol level error (HTTP status + JSON-RPC code), CONTRACT §4.2."""

    def __init__(self, http_status, rpc_code, message):
        super().__init__(message)
        self.http_status = http_status
        self.rpc_code = rpc_code
        self.message = message


class XtdAiAuthError(XtdAiRpcError):
    """Authentication failure of an ``xtd_ai`` request."""

    def __init__(
        self, http_status, rpc_code, message, reason="", user_id=None, run_id=None
    ):
        super().__init__(http_status, rpc_code, message)
        self.reason = reason  # short machine reason for the audit (never a token)
        self.user_id = user_id
        self.run_id = run_id
