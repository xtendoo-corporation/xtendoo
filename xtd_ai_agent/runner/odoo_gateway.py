"""``OdooGateway`` port implemented in process (CONTRACT section 15).

Every call revalidates the run (token checks 4-7) with a fresh view of the
database, builds the runner environment and dispatches the MCP method in
process. Protocol errors are mapped to the neutral errors of the domain.
"""

import json
import logging

from odoo import tools

from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiRpcError

from ..agent.errors import (
    OdooAuthError,
    OdooForbiddenError,
    OdooInvalidParams,
    OdooMethodNotFound,
    OdooServerError,
    RunCancelled,
)
from ..agent.types import Attachment, History, Reply, ToolOutcome, ToolSpec

_logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"


def map_rpc_error(exc):
    """Translate a gateway protocol error to a neutral domain error."""
    message = str(exc.message)[:200]
    code = exc.rpc_code
    if code == -32004 or exc.http_status == 409:
        return RunCancelled(message, code=code)
    if code == -32001 or exc.http_status == 401:
        return OdooAuthError(message, code=code)
    if code == -32003 or exc.http_status == 403:
        return OdooForbiddenError(message, code=code)
    if code == -32601:
        return OdooMethodNotFound(message, code=code)
    if code == -32602:
        return OdooInvalidParams(message, code=code)
    return OdooServerError(message, code=code)


class OdooRunGateway:
    def __init__(self, env, run, *, commit=True):
        self._env = env
        self._run = run.sudo()  # sudo: control record of the gateway
        # tests run in one transaction where commit is forbidden
        self._commit = commit and not tools.config["test_enable"]

    def __repr__(self):
        return f"OdooRunGateway(run={self._run.id})"

    # -- plumbing --------------------------------------------------------
    def _runner_env(self):
        env = self._env
        if self._commit:
            # Make the work so far durable and take a fresh snapshot: a
            # cancellation committed meanwhile by the user must be visible.
            env.flush_all()
            env.cr.commit()
        env.invalidate_all()
        try:
            return env["xtd.ai.run"]._xtd_ai_runner_env(self._run)
        except XtdAiRpcError as exc:
            raise map_rpc_error(exc) from None

    def _call(self, method, params=None):
        env = self._runner_env()
        try:
            return env["xtd.ai.mcp"]._xtd_ai_dispatch(method, params or {})
        except XtdAiRpcError as exc:
            raise map_rpc_error(exc) from None

    # -- port ------------------------------------------------------------
    def check_active(self):
        self._runner_env()

    def initialize(self):
        self._call(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "clientInfo": {"name": "xtd_ai_agent", "version": "1.0.0"},
            },
        )

    def history(self):
        return History.from_payload(self._call("xtd_ai/history"))

    def list_tools(self):
        result = self._call("tools/list")
        tools = [
            ToolSpec(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t["inputSchema"],
                read_only=bool((t.get("annotations") or {}).get("readOnlyHint")),
            )
            for t in result.get("tools", [])
        ]
        return sorted(tools, key=lambda t: t.name)  # stable order: prompt cache

    def call_tool(self, name, arguments):
        result = self._call("tools/call", {"name": name, "arguments": arguments})
        text = ""
        for block in result.get("content") or []:
            if block.get("type") == "text":
                text = block.get("text", "")
                break
        if not text and "structuredContent" in result:
            text = json.dumps(result["structuredContent"], ensure_ascii=False)
        return ToolOutcome(text=text, is_error=bool(result.get("isError", False)))

    def post_reply(self, reply: Reply):
        self._call("xtd_ai/post_reply", reply.to_payload())

    def get_attachment(self, attachment_id):
        result = self._call("xtd_ai/attachment", {"id": attachment_id})
        data = result.get("data_base64") if isinstance(result, dict) else None
        if (
            not isinstance(result, dict)
            or result.get("id") != attachment_id
            or not isinstance(data, str)
        ):
            raise OdooServerError("malformed attachment response")
        return Attachment(
            id=attachment_id,
            name=str(result.get("name") or ""),
            mimetype=str(result.get("mimetype") or ""),
            data_base64=data,
        )
