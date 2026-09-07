from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mcp_enabled = fields.Boolean(
        string="Enable MCP Access",
        help="Master switch to enable or disable all MCP server functionality. "
        "When disabled, all MCP endpoints (the native /mcp JSON-RPC endpoint, the "
        "REST API and the XML-RPC proxy) will return errors and deny access to "
        "any MCP operations.",
        config_parameter="mcp_server.enabled",
        default=False,
    )
    mcp_enable_oauth = fields.Boolean(
        config_parameter="mcp_server.enable_oauth",
        default=True,
        string="Enable OAuth 2.1 Access",
        help="Allow browser MCP clients (Claude.ai, Gemini) to connect by "
        "logging into Odoo via the built-in OAuth 2.1 flow, in addition to API "
        "keys. Enabled by default. Turn it off to disable the /mcp/oauth/* "
        "endpoints and OAuth discovery and accept only API-key auth.",
    )
    mcp_request_limit = fields.Integer(
        string="Request Limit per Minute",
        help="Maximum number of API requests allowed per user per minute. "
        "Set to 0 to disable rate limiting and allow unlimited requests. "
        "This helps prevent API abuse and ensures fair usage across all users. "
        "Default: 300 requests/minute.",
        config_parameter="mcp_server.request_limit",
        default=300,
    )
    mcp_enable_logging = fields.Boolean(
        string="Enable Request Logging",
        help="When enabled, all MCP API requests and responses will be logged for "
        "auditing and debugging purposes. This includes request details, response "
        "times, and any errors. Useful for monitoring API usage and troubleshooting.",
        config_parameter="mcp_server.enable_logging",
        default=True,
    )
    mcp_enable_rate_limiting = fields.Boolean(
        string="Enable Rate Limiting",
        help="When enabled, enforces the request limit per minute for each user. "
        "Disabled by default. The counter is held in memory per Odoo worker "
        "process, so with multiple workers the effective limit is roughly "
        "(workers x limit) and is not a strict global cap - treat it as "
        "best-effort abuse protection, not a hard quota. For a true global "
        "limit use a shared store or an upstream proxy. Configure the limit "
        "with 'Request Limit per Minute'.",
        config_parameter="mcp_server.enable_rate_limiting",
        default=False,
    )
    mcp_log_retention_days = fields.Integer(
        string="Log Retention (days)",
        help="Number of days to keep MCP log entries. Logs older than this will be "
        "automatically deleted to save storage space. Set to 0 to keep logs forever. "
        "Default: 30 days.",
        config_parameter="mcp_server.log_retention_days",
        default=30,
    )
    mcp_default_limit = fields.Integer(
        string="Default Record Limit",
        help="Number of records a read tool returns when the client does not "
        "request a specific limit. Applies to search_records and "
        "aggregate_records. Default: 10.",
        config_parameter="mcp_server.default_limit",
        default=10,
    )
    mcp_max_limit = fields.Integer(
        string="Maximum Record Limit",
        help="Hard cap on the number of records a read tool may return in a "
        "single request. A client asking for more is clamped to this value. "
        "Default: 100.",
        config_parameter="mcp_server.max_limit",
        default=100,
    )
    mcp_max_smart_fields = fields.Integer(
        string="Maximum Smart Fields",
        help="Maximum number of fields chosen by smart field selection when the "
        "client does not list explicit fields. Keeps tool output compact and "
        "LLM-friendly. Default: 15.",
        config_parameter="mcp_server.max_smart_fields",
        default=15,
    )
    mcp_max_related_items = fields.Integer(
        string="Maximum Related Items",
        help="In get_record, related records (one2many/many2many) are listed "
        "inline by name up to this many; larger collections collapse to a count "
        "plus a search hint. Set 0 to always collapse. Default: 3.",
        config_parameter="mcp_server.max_related_items",
        default=3,
    )
    mcp_allowed_origins = fields.Char(
        string="Allowed Browser Origins",
        help="Comma-separated list of browser Origin values allowed to call "
        "the MCP endpoint, e.g. 'https://app.example.com'. Leave empty to "
        "accept requests regardless of Origin (default). When set, a request "
        "whose Origin header is not on the list is refused with HTTP 403 "
        "(MCP DNS-rebinding protection). Requests without an Origin header — "
        "all native MCP clients such as Claude Desktop or Cursor — are "
        "always accepted; the header is only sent by browsers.",
        config_parameter="mcp_server.allowed_origins",
    )

    def set_values(self):
        result = super().set_values()
        # sudo: admin-managed system params; Settings is gated by Administration.
        params = self.env["ir.config_parameter"].sudo()  # admin-managed config

        # The runtime readers (utils.is_mcp_enabled, rate limiting) expect the
        # literal "True"/"False"/"0" strings. The base mechanism stores a
        # boolean False (or integer 0) by deleting the param, which would fall
        # the readers back to their defaults -- so write every value explicitly.
        params.set_param("mcp_server.enabled", str(self.mcp_enabled))
        params.set_param("mcp_server.enable_oauth", str(self.mcp_enable_oauth))
        params.set_param("mcp_server.request_limit", str(self.mcp_request_limit))
        params.set_param("mcp_server.enable_logging", str(self.mcp_enable_logging))
        params.set_param(
            "mcp_server.enable_rate_limiting", str(self.mcp_enable_rate_limiting)
        )
        params.set_param(
            "mcp_server.log_retention_days", str(self.mcp_log_retention_days)
        )
        params.set_param("mcp_server.default_limit", str(self.mcp_default_limit))
        params.set_param("mcp_server.max_limit", str(self.mcp_max_limit))
        params.set_param("mcp_server.max_smart_fields", str(self.mcp_max_smart_fields))
        params.set_param(
            "mcp_server.max_related_items", str(self.mcp_max_related_items)
        )
        # A Char: write the stripped value; empty deletes the param, which the
        # runtime reader (utils.get_allowed_origins) reads as "no restriction".
        params.set_param(
            "mcp_server.allowed_origins", (self.mcp_allowed_origins or "").strip()
        )

        # Flush the @ormcache backing every MCP decision -- the per-model gates
        # AND the global switches (is_mcp_enabled / is_oauth_enabled /
        # get_allowed_origins) -- so a config change (e.g. the master kill-switch)
        # takes effect immediately. registry.clear_cache() also signals the other
        # workers via DB signaling, so the change propagates cross-worker on their
        # next request rather than after a TTL.
        self.env.registry.clear_cache()

        return result
