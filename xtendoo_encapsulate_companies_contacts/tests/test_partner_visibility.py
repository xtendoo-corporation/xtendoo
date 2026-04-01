from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPartnerVisibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Visibility Company B'})

        cls.user_a = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Visibility User A',
            'login': 'visibility_user_a',
            'email': 'visibility_user_a@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        cls.user_b = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Visibility User B',
            'login': 'visibility_user_b',
            'email': 'visibility_user_b@example.com',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
        })
        cls.user_ab = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Visibility User AB',
            'login': 'visibility_user_ab',
            'email': 'visibility_user_ab@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])],
        })

    def _partner_env(self, user):
        return self.env['res.partner'].with_user(user).with_context(allowed_company_ids=user.company_ids.ids)

    def _company_env(self, user):
        return self.env['res.company'].with_user(user).with_context(allowed_company_ids=user.company_ids.ids)

    def test_company_partner_visibility_is_limited_to_its_company(self):
        self.assertFalse(self.company_b.partner_id.company_id)
        self.assertEqual(self.company_b.partner_id.xt_visibility_company_ids, self.company_b)

        visible_partner_ids = self._partner_env(self.user_a).search([('id', '=', self.company_b.partner_id.id)]).ids
        self.assertFalse(visible_partner_ids)

    def test_user_partner_visibility_uses_user_companies(self):
        self.assertEqual(self.user_b.partner_id.company_id, self.company_b)
        self.assertEqual(self.user_b.partner_id.xt_visibility_company_ids, self.company_b)

        user_a_visible_ids = self._partner_env(self.user_a).search([('id', '=', self.user_b.partner_id.id)]).ids
        self.assertFalse(user_a_visible_ids)

        user_b_visible_ids = self._partner_env(self.user_b).search([('id', '=', self.user_b.partner_id.id)]).ids
        self.assertEqual(user_b_visible_ids, [self.user_b.partner_id.id])

    def test_global_partner_is_visible_to_other_companies(self):
        global_partner = self.env['res.partner'].create({
            'name': 'Visibility Global Partner',
            'xt_is_global_visibility': True,
        })

        visible_partner_ids = self._partner_env(self.user_a).search([('id', '=', global_partner.id)]).ids
        self.assertEqual(visible_partner_ids, [global_partner.id])

    def test_only_full_company_admin_can_set_global_partner_visibility(self):
        with self.assertRaises(AccessError):
            self.user_a.partner_id.with_user(self.user_a).write({'xt_is_global_visibility': True})

        self.user_a.partner_id.write({'xt_is_global_visibility': True})
        self.assertTrue(self.user_a.partner_id.xt_is_global_visibility)

    def test_company_visibility_uses_current_user_company_ids(self):
        user_a_visible_company_ids = self._company_env(self.user_a).search([('id', '=', self.company_b.id)]).ids
        self.assertFalse(user_a_visible_company_ids)

        user_ab_visible_company_ids = self._company_env(self.user_ab).search([('id', '=', self.company_b.id)]).ids
        self.assertEqual(user_ab_visible_company_ids, [self.company_b.id])

    def test_existing_single_company_user_partner_gets_company_id(self):
        partner = self.env['res.partner'].with_context(skip_company_encapsulation=True).create({
            'name': 'Visibility Existing User Partner',
            'company_id': False,
        })
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Visibility Existing User',
            'login': 'visibility_existing_user',
            'partner_id': partner.id,
            'company_id': self.company_b.id,
            'company_ids': [(6, 0, [self.company_b.id])],
        })

        self.assertEqual(user.partner_id.company_id, self.company_b)

    def test_multi_company_user_partner_keeps_shared_company_id(self):
        partner = self.env['res.partner'].create({'name': 'Visibility Multi Company Partner'})
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Visibility Multi Company User',
            'login': 'visibility_multi_company_user',
            'partner_id': partner.id,
            'company_id': self.company_a.id,
            'company_ids': [(6, 0, [self.company_a.id, self.company_b.id])],
        })

        self.assertFalse(user.partner_id.company_id)

    def test_email_is_not_required_in_partner_views(self):
        partner_model = self.env['res.partner']

        form_arch = etree.fromstring(
            partner_model.get_view(view_id=self.env.ref('base.view_partner_form').id, view_type='form')['arch']
        )
        main_email_nodes = form_arch.xpath("//sheet//div[contains(@class, 'mb8')]//field[@name='email']")
        child_email_nodes = form_arch.xpath("//page[@name='contact_addresses']//form//field[@name='email']")
        self.assertTrue(main_email_nodes)
        self.assertTrue(child_email_nodes)
        for node in main_email_nodes + child_email_nodes:
            self.assertIn(node.get('required'), (None, 'False', '0'))

        simple_arch = etree.fromstring(
            partner_model.get_view(view_id=self.env.ref('base.view_partner_simple_form').id, view_type='form')['arch']
        )
        simple_email_nodes = simple_arch.xpath("//group//field[@name='email']")
        self.assertTrue(simple_email_nodes)
        for node in simple_email_nodes:
            self.assertIn(node.get('required'), (None, 'False', '0'))

