from odoo.tests.common import TransactionCase


class PortalCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write(
            {
                "portal_attendance_enabled": True,
                "portal_attendance_location_policy": "optional",
                "portal_attendance_max_accuracy": 100,
                "portal_attendance_link_hours": 48,
                "portal_attendance_session_days": 90,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Ana Portal", "company_id": cls.company.id}
        )
        cls.other = cls.env["hr.employee"].create(
            {"name": "Beto Portal", "company_id": cls.company.id}
        )
        cls.Access = cls.env["hr.attendance.portal.access"]
        cls.Punch = cls.env["hr.attendance.portal.punch"]

    def _activate(self, employee=None):
        access, token = self.Access._create_pending(employee or self.employee)
        access, session = self.Access._redeem(token, device_info="test")
        return access, session
