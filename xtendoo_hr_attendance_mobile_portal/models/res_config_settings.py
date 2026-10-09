from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    portal_attendance_enabled = fields.Boolean(
        related="company_id.portal_attendance_enabled", readonly=False
    )
    portal_attendance_link_hours = fields.Integer(
        related="company_id.portal_attendance_link_hours", readonly=False
    )
    portal_attendance_session_days = fields.Integer(
        related="company_id.portal_attendance_session_days", readonly=False
    )
    portal_attendance_location_policy = fields.Selection(
        related="company_id.portal_attendance_location_policy", readonly=False
    )
    portal_attendance_max_accuracy = fields.Integer(
        related="company_id.portal_attendance_max_accuracy", readonly=False
    )
    portal_attendance_privacy_text = fields.Text(
        related="company_id.portal_attendance_privacy_text", readonly=False
    )
