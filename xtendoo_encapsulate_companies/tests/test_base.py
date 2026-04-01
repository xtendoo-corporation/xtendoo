from odoo.tests.common import TransactionCase


class TestBaseCompanyEncapsulation(TransactionCase):
    def test_allowed_company_context_has_priority(self):
        other_company = self.env['res.company'].create({'name': 'Legacy Context Company'})

        partner = self.env['res.partner'].with_context(
            allowed_company_ids=[other_company.id],
            default_company_id=other_company.id,
        ).create({'name': 'Legacy Context Partner'})

        self.assertEqual(partner.company_id, other_company)

    def test_chart_template_load_does_not_force_account_group_to_user_company(self):
        other_company = self.env['res.company'].create({'name': 'Legacy Account Group Company'})

        group = self.env['account.group'].with_context(
            allowed_company_ids=[other_company.id],
            default_company_id=other_company.id,
            chart_template_load=True,
        ).create({
            'name': 'Legacy Chart Template Group',
            'code_prefix_start': '999993',
        })

        self.assertEqual(group.company_id, other_company)

    def test_global_ir_default_keeps_shared_company_id(self):
        field = self.env['ir.model.fields']._get('res.partner', 'property_stock_customer')

        default = self.env['ir.default'].create({
            'field_id': field.id,
            'json_value': 'false',
            'user_id': False,
            'company_id': False,
            'condition': False,
        })

        self.assertFalse(default.company_id)

