from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    portal_attendance_enabled = fields.Boolean(
        string="Mobile punch portal",
        help="Allow employees of this company to punch in/out from the mobile portal.",
    )
    portal_attendance_link_hours = fields.Integer(
        string="Activation link validity (hours)", default=48
    )
    portal_attendance_session_days = fields.Integer(
        string="Device session validity (days)", default=90
    )
    portal_attendance_location_policy = fields.Selection(
        [
            ("optional", "Punch anyway, flagging the missing location"),
            ("required", "Reject the punch without a valid location"),
        ],
        string="Location policy",
        default="optional",
        required=True,
    )
    portal_attendance_max_accuracy = fields.Integer(
        string="Maximum accepted accuracy (m)",
        default=100,
        help="Locations less accurate than this are flagged as low accuracy "
        "(or rejected when the location policy is 'required').",
    )
    portal_attendance_privacy_text = fields.Text(
        string="Location notice",
        translate=True,
        help="Text shown to the employee under the punch button. Leave empty "
        "to use the default notice.",
    )
