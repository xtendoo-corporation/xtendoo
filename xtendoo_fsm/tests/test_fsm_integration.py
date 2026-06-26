# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import TransactionCase


class TestFSMIntegration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Integration Test Customer',
            'email': 'integration@test.com',
            'is_company': True,
        })
        self.employee = self.env['hr.employee'].create({'name': 'Integration Test Technician'})
        self.env['fsm.stage'].create({
            'name': 'Integration Test Stage',
            'code': 'integration_stage',
            'is_default': True,
        })

    def test_hr_employee_and_mail_integration(self):
        fsm_order = self.env['fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Integration test',
            'responsible_id': self.employee.id,
            'person_ids': [(6, 0, [self.employee.id])],
        })

        self.assertEqual(fsm_order.responsible_id, self.employee)
        self.assertIn(self.employee, fsm_order.person_ids)
        message = fsm_order.message_post(body='Test message for FSM order')
        self.assertIn(message, fsm_order.message_ids)

    def test_sale_order_integration(self):
        fsm_order = self.env['fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Integration test with sales',
        })

        result = fsm_order.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(result['res_id'])

        self.assertEqual(sale_order.partner_id, self.partner)
        self.assertEqual(sale_order.fsm_order_id, fsm_order)
