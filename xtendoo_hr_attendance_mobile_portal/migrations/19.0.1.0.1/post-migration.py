from odoo import SUPERUSER_ID, api

OLD_DEFAULT = (
    "Your location is requested only when you press the punch button, "
    "and is stored together with the punch to document it. It is not "
    "tracked at any other time."
)


def migrate(cr, version):
    """The notice used to be stored (in English) at install time. Empty it so
    the translatable default of the template is used, unless it was edited."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].with_context(active_test=False).search([]):
        if company.with_context(lang="en_US").portal_attendance_privacy_text == OLD_DEFAULT:
            company.portal_attendance_privacy_text = False
