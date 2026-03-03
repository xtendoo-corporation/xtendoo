from . import models


def _post_init_hook(env):
    """Override noupdate CRM rules to support see_all_companies bypass."""
    rules = {
        'crm.crm_lead_company_rule': (
            "[(1, '=', 1)] if user.see_all_companies else "
            "[('company_id', 'in', company_ids + [False])]"
        ),
        'crm.crm_activity_report_rule_multi_company': (
            "[(1, '=', 1)] if user.see_all_companies else "
            "[('company_id', 'in', company_ids + [False])]"
        ),
    }
    for xml_id, domain in rules.items():
        rule = env.ref(xml_id, raise_if_not_found=False)
        if rule:
            rule.sudo().write({'domain_force': domain})

