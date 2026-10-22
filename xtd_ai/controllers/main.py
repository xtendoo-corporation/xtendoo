import json

from odoo import http
from odoo.http import request


class XtdAiGatewayController(http.Controller):
    @http.route(
        "/xtd_ai/mcp",
        type="http",
        auth="xtd_ai",
        methods=["POST"],
        csrf=False,
        max_content_length=1024 * 1024,
    )
    def mcp(self, **kwargs):
        """Single JSON-RPC 2.0 message from the AI service (CONTRACT §4)."""
        try:
            message = json.loads(request.httprequest.get_data(as_text=True))
        except ValueError:
            return request.make_json_response(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                },
                status=200,
            )
        status, response = request.env["xtd.ai.mcp"]._xtd_ai_handle(message)
        return request.make_json_response(
            response, headers=[("Cache-Control", "no-store")], status=status
        )
