from odoo import fields, models

LOCATION_STATUS = [
    ("ok", "Obtained from browser (unverified)"),
    ("low_accuracy", "Obtained, low accuracy"),
    ("denied", "Permission denied"),
    ("declined", "Not shared by the employee"),
    ("unavailable", "Unavailable"),
]


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    in_mode = fields.Selection(
        selection_add=[("mobile_portal", "Mobile portal")],
        ondelete={"mobile_portal": "set default"},
    )
    out_mode = fields.Selection(
        selection_add=[("mobile_portal", "Mobile portal")],
        ondelete={"mobile_portal": "set default"},
    )
    in_accuracy = fields.Float(
        string="Accuracy (m) (In)", digits=(10, 1), readonly=True, aggregator=None
    )
    out_accuracy = fields.Float(
        string="Accuracy (m) (Out)", digits=(10, 1), readonly=True, aggregator=None
    )
    in_location_status = fields.Selection(
        LOCATION_STATUS, string="Location status (In)", readonly=True
    )
    out_location_status = fields.Selection(
        LOCATION_STATUS, string="Location status (Out)", readonly=True
    )
