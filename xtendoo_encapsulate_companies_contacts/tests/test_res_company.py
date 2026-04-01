from odoo.tests.common import TransactionCase


class TestCompanyPartnerEncapsulation(TransactionCase):
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

