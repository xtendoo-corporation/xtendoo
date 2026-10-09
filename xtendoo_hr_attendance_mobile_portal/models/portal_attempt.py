import hashlib
import hmac
from datetime import timedelta

from odoo import api, fields, models

MAX_FAILED_ATTEMPTS = 5
WINDOW_MINUTES = 15


class PortalAttempt(models.Model):
    """Failed activation attempts, used to throttle token guessing per IP.

    Only a keyed hash of the IP is stored, never the address itself.
    """

    _name = "hr.attendance.portal.attempt"
    _description = "Mobile punch portal failed attempt"

    ip_hash = fields.Char(required=True, index=True)

    @api.model
    def _hash_ip(self, ip):
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret") or ""
        return hmac.new(secret.encode(), (ip or "").encode(), hashlib.sha256).hexdigest()

    @api.model
    def _is_blocked(self, ip):
        since = fields.Datetime.now() - timedelta(minutes=WINDOW_MINUTES)
        return (
            self.sudo().search_count(
                [("ip_hash", "=", self._hash_ip(ip)), ("create_date", ">=", since)]
            )
            >= MAX_FAILED_ATTEMPTS
        )

    @api.model
    def _register_failure(self, ip):
        self.sudo().create({"ip_hash": self._hash_ip(ip)})

    @api.autovacuum
    def _gc_attempts(self):
        limit = fields.Datetime.now() - timedelta(days=1)
        self.sudo().search([("create_date", "<", limit)]).unlink()
