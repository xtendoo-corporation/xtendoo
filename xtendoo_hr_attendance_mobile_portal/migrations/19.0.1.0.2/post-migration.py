from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Give existing employees of enabled companies a visible activation link."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["hr.employee"].search(
        [("company_id.portal_attendance_enabled", "=", True)]
    )._portal_ensure_link()
