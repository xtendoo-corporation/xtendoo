from odoo.tests.common import TransactionCase


class TestCompanyPartnerEncapsulation(TransactionCase):
    def test_allowed_company_context_has_priority_over_user_company(self):
        other_company = self.env['res.company'].create({'name': 'Encapsulated Context Company'})

        partner = self.env['res.partner'].with_context(
            allowed_company_ids=[other_company.id],
        ).create({'name': 'Encapsulated Context Partner'})

        self.assertEqual(partner.company_id, other_company)

    def test_company_partner_is_created_shared(self):
        company = self.env['res.company'].create({'name': 'Encapsulated Shared Company'})

        self.assertFalse(company.partner_id.company_id)

    def test_regular_partner_keeps_current_company(self):
        partner = self.env['res.partner'].create({'name': 'Encapsulated Regular Partner'})

        self.assertEqual(partner.company_id, self.env.user.company_id)

    def test_sanitizer_resets_company_partner_company_id(self):
        company = self.env['res.company'].create({'name': 'Company To Sanitize'})
        company.partner_id.write({'company_id': self.env.company.id})

        self.env['res.company']._xt_ensure_company_partners_shared()

        self.assertFalse(company.partner_id.company_id)

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

    def test_sanitizer_resets_shared_mto_route_company(self):
        if 'stock.route' not in self.env:
            self.skipTest('Stock no está instalado en esta base de test')

        route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
        if not route:
            self.skipTest('La ruta MTO global no existe en esta base de test')

        route.write({'company_id': self.env.company.id})

        self.env['res.company']._xt_ensure_company_partners_shared()

        self.assertFalse(route.company_id)

    def test_chart_template_load_does_not_force_account_group_to_user_company(self):
        if 'account.group' not in self.env:
            self.skipTest('Accounting no está instalado en esta base de test')

        other_company = self.env['res.company'].create({'name': 'Encapsulated Account Group Company'})

        group = self.env['account.group'].with_context(
            allowed_company_ids=[other_company.id],
            default_company_id=other_company.id,
            chart_template_load=True,
        ).create({
            'name': 'Encapsulated Chart Template Group',
            'code_prefix_start': '999991',
        })

        self.assertEqual(group.company_id, other_company)

