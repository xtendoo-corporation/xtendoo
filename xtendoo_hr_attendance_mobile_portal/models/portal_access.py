import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models

# Re-write ``last_used`` at most this often, to avoid a write per request.
LAST_USED_GRANULARITY = timedelta(minutes=5)


def _hash(token):
    # Tokens carry 256 bits of entropy, so a plain SHA-256 is enough (no
    # need for a slow, salted KDF as with human-chosen passwords).
    return hashlib.sha256(token.encode()).hexdigest()


class PortalAccess(models.Model):
    """One row per activation link / device session of an employee.

    Authentication of the portal only: it knows nothing about attendances.
    """

    _name = "hr.attendance.portal.access"
    _description = "Mobile punch portal access"
    _order = "id desc"

    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(
        related="employee_id.company_id", store=True, index=True
    )
    state = fields.Selection(
        [("pending", "Pending activation"), ("active", "Active"), ("revoked", "Revoked")],
        default="pending",
        required=True,
        index=True,
    )
    # Only hashes are stored; the plain tokens are never persisted.
    activation_hash = fields.Char(index=True, copy=False)
    activation_expires = fields.Datetime(copy=False)
    session_hash = fields.Char(index=True, copy=False)
    session_expires = fields.Datetime(copy=False)
    activated_on = fields.Datetime(readonly=True, copy=False)
    last_used = fields.Datetime(readonly=True, copy=False)
    device_info = fields.Char(readonly=True, copy=False)
    is_expired = fields.Boolean(compute="_compute_is_expired")

    @api.depends("state", "activation_expires", "session_expires")
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for access in self:
            limit = (
                access.activation_expires
                if access.state == "pending"
                else access.session_expires
            )
            access.is_expired = bool(
                access.state != "revoked" and limit and limit < now
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @api.model
    def _create_pending(self, employee):
        """Return ``(access, plain_activation_token)``."""
        company = employee.company_id
        token = secrets.token_urlsafe(32)
        access = self.create(
            {
                "employee_id": employee.id,
                "activation_hash": _hash(token),
                "activation_expires": fields.Datetime.now()
                + timedelta(hours=max(company.portal_attendance_link_hours, 1)),
            }
        )
        return access, token

    @api.model
    def _redeem(self, token, device_info=None):
        """Exchange a valid, unused activation token for a device session.

        Returns ``(access, plain_session_token)`` or ``(None, None)``.
        While a device is bound the link cannot be used again (state is no
        longer ``pending``); it becomes usable again only if the device is
        unlinked (see ``action_unlink_device``).
        """
        if not token or len(token) > 128:
            return None, None
        now = fields.Datetime.now()
        access = self.sudo().search(
            [
                ("state", "=", "pending"),
                ("activation_hash", "=", _hash(token)),
                ("activation_expires", ">", now),
            ],
            limit=1,
        )
        if not access:
            return None, None
        # Row lock: two simultaneous redemptions of the same link must not
        # both succeed.
        self.env.cr.execute(
            "SELECT id FROM hr_attendance_portal_access WHERE id = %s FOR UPDATE",
            [access.id],
        )
        access.invalidate_recordset()
        if access.state != "pending":
            return None, None
        session_token = secrets.token_urlsafe(32)
        days = max(access.company_id.portal_attendance_session_days, 1)
        access.write(
            {
                "state": "active",
                "session_hash": _hash(session_token),
                "session_expires": now + timedelta(days=days),
                "activated_on": now,
                "last_used": now,
                "device_info": (device_info or "")[:200],
            }
        )
        return access, session_token

    @api.model
    def _resolve_session(self, session_token):
        """Return the employee-bound access for a session cookie, or an empty
        recordset. Checks expiry, revocation, company switch and archiving."""
        if not session_token or len(session_token) > 128:
            return self.browse()
        now = fields.Datetime.now()
        access = self.sudo().search(
            [
                ("state", "=", "active"),
                ("session_hash", "=", _hash(session_token)),
                ("session_expires", ">", now),
            ],
            limit=1,
        )
        if not access:
            return access
        employee = access.employee_id
        if not employee.active or not employee.company_id.portal_attendance_enabled:
            return self.browse()
        if not access.last_used or now - access.last_used > LAST_USED_GRANULARITY:
            access.last_used = now
        return access

    def action_revoke(self):
        self.write(
            {
                "state": "revoked",
                "activation_hash": False,
                "session_hash": False,
            }
        )

    def action_unlink_device(self):
        """Log the bound device out and make the SAME activation link usable
        again (with a fresh validity window), e.g. when the employee changes
        phone. Revoked accesses stay revoked."""
        now = fields.Datetime.now()
        for access in self.filtered(lambda a: a.state == "active"):
            hours = max(access.company_id.portal_attendance_link_hours, 1)
            access.write(
                {
                    "state": "pending",
                    "session_hash": False,
                    "session_expires": False,
                    "activated_on": False,
                    "device_info": False,
                    "activation_expires": now + timedelta(hours=hours),
                }
            )

    def action_renew(self):
        """Replace this access: cut the current device/link and issue a new
        one-time activation link for the same employee."""
        self.ensure_one()
        employee = self.employee_id
        self.action_revoke()
        return employee.action_portal_generate_link()

    @api.autovacuum
    def _gc_accesses(self):
        """Drop dead rows: expired links and sessions, and old revocations."""
        now = fields.Datetime.now()
        limit = now - timedelta(days=30)
        self.sudo().search(
            [
                "|",
                "|",
                "&", ("state", "=", "pending"), ("activation_expires", "<", limit),
                "&", ("state", "=", "active"), ("session_expires", "<", limit),
                "&", ("state", "=", "revoked"), ("write_date", "<", limit),
            ]
        ).unlink()
