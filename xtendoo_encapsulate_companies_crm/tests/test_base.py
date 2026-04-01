from odoo.tests.common import TransactionCase


class TestCrmCompanyEncapsulation(TransactionCase):
    def test_allowed_company_context_has_priority_for_crm_team(self):
        other_company = self.env['res.company'].create({'name': 'CRM Context Company'})

        team = self.env['crm.team'].with_context(
            allowed_company_ids=[other_company.id],
            default_company_id=other_company.id,
        ).create({
            'name': 'CRM Context Team',
        })

        self.assertEqual(team.company_id, other_company)

    def test_chart_template_load_does_not_force_account_group_to_user_company(self):
        if 'account.group' not in self.env:
            self.skipTest('Accounting no está instalado en esta base de test')

        other_company = self.env['res.company'].create({'name': 'CRM Account Group Company'})

        group = self.env['account.group'].with_context(
            allowed_company_ids=[other_company.id],
            default_company_id=other_company.id,
            chart_template_load=True,
        ).create({
            'name': 'CRM Chart Template Group',
            'code_prefix_start': '999992',
        })

        self.assertEqual(group.company_id, other_company)

