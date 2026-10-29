import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

TEXT_LIMIT = 300
AUTH_FAILED_BURST = 100  # max auth_failed rows per minute (flood protection)


def truncate_texts(value, depth=0):
    """Return a JSON-safe copy of ``value`` with every string cut to 300 chars."""
    if depth > 6:
        return None
    if isinstance(value, str):
        return value if len(value) <= TEXT_LIMIT else value[:TEXT_LIMIT] + "..."
    if isinstance(value, dict):
        return {str(k): truncate_texts(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [truncate_texts(v, depth + 1) for v in value[:100]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:TEXT_LIMIT]


class XtdAiAudit(models.Model):
    _name = "xtd.ai.audit"
    _description = "AI agent audit log"
    _order = "id desc"

    run_id = fields.Many2one(
        "xtd.ai.run", ondelete="set null", index=True, readonly=True
    )
    user_id = fields.Many2one(
        "res.users", ondelete="set null", index=True, readonly=True
    )
    company_id = fields.Many2one("res.company", ondelete="set null", readonly=True)
    event = fields.Selection(
        [
            ("tool_call", "Tool call"),
            ("auth_failed", "Authentication failed"),
            ("confirm", "Confirmation"),
            ("cancel", "Cancellation"),
            ("guard_blocked", "Guard blocked"),
            ("attachment_read", "Attachment read"),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    tool_name = fields.Char(readonly=True)
    arguments = fields.Json(readonly=True)
    outcome = fields.Selection(
        [
            ("ok", "OK"),
            ("error", "Error"),
            ("pending", "Pending"),
            ("denied", "Denied"),
        ],
        required=True,
        readonly=True,
    )
    error_code = fields.Char(readonly=True)
    record_refs = fields.Json(readonly=True)
    duration_ms = fields.Integer(readonly=True)

    # ------------------------------------------------------------------
    # Immutability: the log is written only by the gateway (see _xtd_ai_log)
    # ------------------------------------------------------------------
    def write(self, vals):  # pylint: disable=method-required-super
        # Append-only by design: write never reaches super().
        raise AccessError(self.env._("The AI audit log is immutable."))

    def unlink(self):
        # Deliberate: the audit log is append-only; only the purge cron may delete.
        # pylint: disable=no-raise-unlink
        if not self.env.context.get("_xtd_ai_audit_purge"):
            raise AccessError(self.env._("The AI audit log cannot be deleted."))
        return super().unlink()

    @api.model
    def _xtd_ai_log(self, event, outcome, **values):
        """Create one audit row. Arguments are truncated; tokens are never stored.

        sudo: nobody has create rights on this model (ACL); the gateway is the
        only writer.
        """
        vals = {"event": event, "outcome": outcome}
        for key in (
            "run_id",
            "user_id",
            "company_id",
            "tool_name",
            "error_code",
            "duration_ms",
        ):
            if values.get(key) is not None:
                vals[key] = values[key]
        if values.get("arguments") is not None:
            vals["arguments"] = truncate_texts(values["arguments"])
        if values.get("record_refs") is not None:
            vals["record_refs"] = truncate_texts(values["record_refs"])
        return self.sudo().create(vals)

    @api.model
    def _xtd_ai_log_auth_failed(
        self, dbname_registry, reason, user_id=None, run_id=None
    ):
        """Log an authentication failure on its own cursor (the request is rolled back).

        Never receives the token. Throttled to avoid flooding the table.
        """
        try:
            with dbname_registry.cursor() as cr:
                env = api.Environment(cr, 1, {})
                recent = env["xtd.ai.audit"].search_count(
                    [
                        ("event", "=", "auth_failed"),
                        (
                            "create_date",
                            ">=",
                            fields.Datetime.now() - timedelta(minutes=1),
                        ),
                    ]
                )
                if recent >= AUTH_FAILED_BURST:
                    _logger.warning("xtd_ai auth_failed (throttled): %s", reason)
                    return
                env["xtd.ai.audit"]._xtd_ai_log(
                    "auth_failed",
                    "denied",
                    error_code=reason,
                    user_id=user_id,
                    run_id=run_id,
                )
        except Exception:
            _logger.exception("Could not write the xtd_ai auth_failed audit row")

    @api.model
    def _xtd_ai_cron_purge(self):
        days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtd_ai.audit_retention_days", "365")
            or 365
        )
        limit = fields.Datetime.now() - timedelta(days=max(days, 1))
        old = (
            self.sudo()
            .with_context(_xtd_ai_audit_purge=True)
            .search([("create_date", "<", limit)], limit=10000)
        )
        old.unlink()
