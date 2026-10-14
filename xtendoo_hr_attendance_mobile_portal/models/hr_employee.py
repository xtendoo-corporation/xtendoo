from odoo import api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    portal_access_ids = fields.One2many(
        "hr.attendance.portal.access",
        "employee_id",
        string="Mobile punch accesses",
        groups="hr_attendance.group_hr_attendance_user",
    )

    portal_url = fields.Char(
        string="Portal URL",
        compute="_compute_portal_urls",
        groups="hr_attendance.group_hr_attendance_user",
    )
    portal_activation_url = fields.Char(
        string="Activation link",
        compute="_compute_portal_urls",
        groups="hr_attendance.group_hr_attendance_user",
    )
    portal_activation_expires = fields.Datetime(
        compute="_compute_portal_urls",
        groups="hr_attendance.group_hr_attendance_user",
    )

    @api.depends(
        "portal_access_ids.state",
        "portal_access_ids.activation_token",
        "portal_access_ids.activation_expires",
    )
    def _compute_portal_urls(self):
        now = fields.Datetime.now()
        for employee in self:
            base = employee.get_base_url()
            employee.portal_url = f"{base}/fichaje"
            pending = employee.portal_access_ids.filtered(
                lambda a: a.state == "pending"
                and a.activation_token
                and a.activation_expires
                and a.activation_expires > now
            )[:1]
            employee.portal_activation_url = pending.activation_url or False
            employee.portal_activation_expires = pending.activation_expires or False

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees.filtered(
            lambda e: e.company_id.portal_attendance_enabled
        )._portal_ensure_link()
        return employees

    def _portal_ensure_link(self):
        """Give every employee without a live access a pending activation link."""
        Access = self.env["hr.attendance.portal.access"].sudo()
        for employee in self:
            if not employee.portal_access_ids.sudo().filtered(
                lambda a: a.state != "revoked" and not a.is_expired
            ):
                Access._create_pending(employee)

    def action_portal_generate_link(self):
        """Issue a fresh activation link, replacing any pending one. It stays
        visible (and copyable) in the employee's Mobile punch tab."""
        self.ensure_one()
        Access = self.env["hr.attendance.portal.access"]
        self.portal_access_ids.filtered(lambda a: a.state == "pending").action_revoke()
        Access._create_pending(self)
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def action_portal_send_chat(self):
        """Copy the activation link and open the chat with the employee."""
        self.ensure_one()
        if not self.portal_activation_url:
            self.action_portal_generate_link()
        partner = self.user_id.partner_id or self.work_contact_id
        if not partner:
            raise UserError(
                self.env._("%s has no contact to chat with.", self.name)
            )
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_portal_send_chat",
            "params": {
                "partner_id": partner.id,
                "text": self.env._(
                    "Hi! Activate your mobile punch here: %s",
                    self.portal_activation_url,
                ),
            },
        }

    def action_portal_revoke_all(self):
        self.portal_access_ids.filtered(
            lambda a: a.state != "revoked"
        ).action_revoke()
