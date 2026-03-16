from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_work_center = fields.Boolean(
        string="Work Center",
        default=False,
    )

    def action_open_work_center_confirm(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "name": _("Confirm"),
            "tag": "hr_attendance_work_center_confirm",
            "params": {
                "work_center_id": self.id,
                "work_center_name": self.display_name,
            },
            "target": "main",
        }

