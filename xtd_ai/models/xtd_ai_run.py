import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..tools import token as token_lib
from ..tools.errors import XtdAiAuthError

_logger = logging.getLogger(__name__)

STALE_SECONDS = token_lib.TTL + 120
MAX_RECORD_REFS = 100


class XtdAiRun(models.Model):
    _name = "xtd.ai.run"
    _description = "AI agent run"
    _order = "id desc"

    conversation_id = fields.Many2one(
        "xtd.ai.conversation", required=True, ondelete="cascade", index=True
    )
    user_id = fields.Many2one(
        "res.users", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one("res.company", help="Active company of the run.")
    cids = fields.Json(
        string="Allowed companies",
        help="Company ids allowed for the run (the first one is the active company).",
    )
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="queued",
        required=True,
        index=True,
    )
    jti = fields.Char(required=True, copy=False, groups="base.group_system")
    provider = fields.Char()
    model = fields.Char()
    input_tokens = fields.Integer()
    output_tokens = fields.Integer()
    cache_read_tokens = fields.Integer()
    cache_write_tokens = fields.Integer()
    cost_estimate = fields.Float(digits=(16, 6))
    iterations = fields.Integer()
    tool_calls = fields.Integer(help="Counted by the gateway on each tools/call.")
    started_at = fields.Datetime()
    finished_at = fields.Datetime()
    error = fields.Char()
    record_refs = fields.Json(help="Records returned by the tools during the run.")

    # ------------------------------------------------------------------
    # In-process runner (CONTRACT section 15)
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_revalidate(self, run):
        """Same checks as the token verification (CONTRACT section 2, steps 4-7).

        :raises: ``XtdAiAuthError`` with the same codes as the HTTP auth.
        """
        run = run.sudo()  # sudo: control record of the gateway
        run_id = run.id

        def fail(reason, http_status=401, code=-32001, message="Invalid credentials"):
            raise XtdAiAuthError(
                http_status,
                code,
                message,
                reason=reason,
                user_id=run.user_id.id or None,
                run_id=run_id or None,
            )

        if not run.exists():
            fail("run_mismatch")
        user = run.user_id
        if not (
            user
            and user.active
            and not user.share
            and user._has_group("xtd_ai.group_xtd_ai_user")
        ):
            fail("user_not_allowed")
        if run.state not in ("queued", "running"):
            fail("run_not_active", 409, -32004, "Run is not active")
        conversation = run.conversation_id
        if conversation.state != "open" or conversation.user_id != user:
            fail("conversation_closed")
        if not set(run._xtd_ai_cids()) <= set(user.company_ids.ids):
            fail("company_not_allowed", 403, -32003, "Company not allowed")
        return True

    def _xtd_ai_cids(self):
        self.ensure_one()
        run = self.sudo()
        return list(run.cids or [run.company_id.id or run.user_id.company_id.id])

    @api.model
    def _xtd_ai_runner_env(self, run):
        """Environment of the user for an in-process run, after revalidating it."""
        self._xtd_ai_revalidate(run)
        run = run.sudo()
        user = run.user_id
        return self.env(
            user=user.id,
            su=False,
            context={
                "allowed_company_ids": run._xtd_ai_cids(),
                "lang": user.lang or "en_US",
                "tz": user.tz or "UTC",
                "xtd_ai_run": run.id,
                "mail_auto_subscribe_no_notify": True,
                "mail_notify_force_send": False,
            },
        )

    # ------------------------------------------------------------------
    # Control methods. Users have read-only ACL; everything below writes with
    # sudo (commented) after checking the caller.
    # ------------------------------------------------------------------
    def _xtd_ai_touch_running(self):
        """First authenticated call of a queued run moves it to running."""
        for run in self.filtered(lambda r: r.state == "queued"):
            run.sudo().write({"state": "running", "started_at": fields.Datetime.now()})

    def _xtd_ai_count_tool_call(self):
        """Atomically count one tools/call and return the new total."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE xtd_ai_run SET tool_calls = COALESCE(tool_calls, 0) + 1 "
            "WHERE id = %s RETURNING tool_calls",
            (self.id,),
        )
        self.invalidate_recordset(["tool_calls"])
        return self.env.cr.fetchone()[0]

    def _xtd_ai_add_record_refs(self, refs):
        """Accumulate (deduplicated, capped) record references of the run."""
        self.ensure_one()
        current = list(self.sudo().record_refs or [])
        # The same record may come twice: as a form and as its journal items
        seen = {(r.get("model"), r.get("id"), r.get("view")) for r in current}
        for ref in refs:
            key = (ref.get("model"), ref.get("id"), ref.get("view"))
            if key not in seen and len(current) < MAX_RECORD_REFS:
                seen.add(key)
                current.append(ref)
        self.sudo().record_refs = current

    def _xtd_ai_finish(self, state, error=None, usage=None):
        self.ensure_one()
        usage = usage or {}
        vals = {
            "state": state,
            "finished_at": fields.Datetime.now(),
            "error": (error or "")[:250] or False,
        }
        for key in ("provider", "model"):
            if isinstance(usage.get(key), str):
                vals[key] = usage[key][:100]
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_write_tokens",
            "iterations",
        ):
            value = usage.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                vals[key] = value
        cost = usage.get("cost_estimate")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
            vals["cost_estimate"] = float(cost)
        self.sudo().write(vals)  # sudo: control fields, see class comment

    def _xtd_ai_notify(self, message=None):
        """Tell the browser (bus) that the conversation changed."""
        self.ensure_one()
        run = self.sudo()
        run.user_id.partner_id._bus_send(
            "xtd_ai/update",
            {
                "conversation_id": run.conversation_id.id,
                "message_id": message.id if message else False,
                "run_id": run.id,
                "state": run.state,
            },
        )

    def _xtd_ai_fail(self, error):
        """Mark the run as failed and leave a notice in the chat.

        For the chat routes, e.g. when the AI service cannot be reached.
        """
        self.ensure_one()
        run = self.sudo()
        if run.state not in ("queued", "running"):
            return False
        run._xtd_ai_finish("failed", error=error)
        notice = (
            self.env["xtd.ai.message"]
            .sudo()
            .create(
                {
                    "conversation_id": run.conversation_id.id,
                    "role": "notice",
                    "body": error or _("La ejecución ha fallado."),
                    "run_id": run.id,
                }
            )
        )
        run._xtd_ai_notify(notice)
        return True

    def action_cancel(self):
        """Cancel an own run in progress (chat route /run/cancel)."""
        self.ensure_one()
        if self.env.context.get("xtd_ai_run"):
            raise AccessError(_("Operación no permitida."))
        if self.user_id.id != self.env.uid:
            raise AccessError(_("Esta ejecución no es tuya."))
        run = self.sudo()
        if run.state not in ("queued", "running"):
            raise UserError(_("La ejecución ya ha terminado."))
        run._xtd_ai_finish("cancelled")
        run._xtd_ai_notify()
        return True

    def _xtd_ai_expire_stale(self):
        """Fail runs that stayed queued/running longer than the token lifetime."""
        limit = fields.Datetime.now() - timedelta(seconds=STALE_SECONDS)
        stale = self.sudo().filtered(
            lambda r: r.state in ("queued", "running")
            and (r.create_date or limit) < limit
        )
        for run in stale:
            run._xtd_ai_finish("failed", error="timeout")
        return stale

    @api.model
    def _xtd_ai_cron_housekeeping(self):
        limit = fields.Datetime.now() - timedelta(seconds=STALE_SECONDS)
        self.sudo().search(
            [("state", "in", ("queued", "running")), ("create_date", "<", limit)]
        )._xtd_ai_expire_stale()
        self.env["xtd.ai.pending_action"].sudo()._xtd_ai_expire_old()
