from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    portal_access_ids = fields.One2many(
        "hr.attendance.portal.access",
        "employee_id",
        string="Mobile punch accesses",
        groups="hr_attendance.group_hr_attendance_user",
    )

    def action_portal_generate_link(self):
        """Create a one-time activation link. The plain token is only shown
        here, once: the database keeps just its hash."""
        self.ensure_one()
        access, token = self.env["hr.attendance.portal.access"]._create_pending(self)
        url = f"{access.get_base_url()}/fichaje/activar/{token}"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Activation link for %s", self.name),
                "message": self.env._(
                    "Send this link to the employee (valid until %(date)s). "
                    "It is shown only once and works for a single device: %(url)s",
                    date=access.activation_expires,
                    url=url,
                ),
                "type": "success",
                "sticky": True,
            },
        }

    def action_portal_revoke_all(self):
        self.portal_access_ids.filtered(
            lambda a: a.state != "revoked"
        ).action_revoke()
