from . import models


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
        'base.res_partner_rule': (
            "[(1, '=', 1)] if user.see_all_companies else "
            "['|', '|', '|', ('id', 'in', [1, 2]), ('partner_share', '=', False), "
            "('company_id', 'parent_of', company_ids), ('company_id', '=', False)]"
        ),
    }
    for xml_id, domain in rules.items():
        rule = env.ref(xml_id, raise_if_not_found=False)
        if rule:
            rule.sudo().write({'domain_force': domain})

