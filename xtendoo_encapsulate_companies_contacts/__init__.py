from . import models


PARTNER_RULE_DOMAIN = (
    "[(1, '=', 1)] if user.see_all_companies else "
    "['|', '|', ('id', '=', user.partner_id.id), ('xt_is_global_visibility', '=', True), "
    "('xt_visibility_company_ids', 'in', company_ids)]"
)


def _post_init_hook(env):
    """Override noupdate base rules to support see_all_companies bypass."""
    rules = {
        'base.res_company_rule_employee': (
            "[(1, '=', 1)] if user.see_all_companies else [('id', 'in', company_ids)]"
        ),
        'base.res_company_rule_portal': (
            "[(1, '=', 1)] if user.see_all_companies else [('id', 'in', company_ids)]"
        ),
        'base.res_company_rule_public': (
            "[(1, '=', 1)] if user.see_all_companies else [('id', 'in', company_ids)]"
        ),
        'base.res_users_rule': (
            "[(1, '=', 1)] if user.see_all_companies else "
            "['|', ('share', '=', False), ('company_ids', 'in', company_ids)]"
        ),
        'base.res_partner_rule': PARTNER_RULE_DOMAIN,
    }
    for xml_id, domain in rules.items():
        rule = env.ref(xml_id, raise_if_not_found=False)
        if rule:
            rule.sudo().write({'domain_force': domain})

    env['res.company']._xt_ensure_company_partners_shared()
    env['res.users'].sudo().with_context(active_test=False).search([])._xt_sync_partner_company_ids()
    env['res.partner']._xt_mark_default_global_partners()
    env['res.partner'].with_context(active_test=False).search([])._xt_sync_visibility_companies()

