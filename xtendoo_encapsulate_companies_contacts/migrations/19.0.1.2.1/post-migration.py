from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company']._xt_ensure_company_partners_shared()
    env['res.users'].sudo().with_context(active_test=False).search([])._xt_sync_partner_company_ids()
    env['res.partner']._xt_mark_default_global_partners()
    env['res.partner'].with_context(active_test=False).search([])._xt_sync_visibility_companies()

