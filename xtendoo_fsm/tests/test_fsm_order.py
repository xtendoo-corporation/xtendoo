# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestFSMOrder(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'is_company': True,
        })
        self.employee = self.env['hr.employee'].create({'name': 'Test Technician'})
        self.stage = self.env['fsm.stage'].create({
            'name': 'Test Stage',
            'code': 'test_stage',
            'is_default': True,
        })
        self.tag = self.env['fsm.tag'].create({'name': 'Test Tag', 'color': 1})

    def test_fsm_order_creation(self):
        order = self.env['fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test work order',
            'tag_ids': [(6, 0, [self.tag.id])],
        })

        self.assertTrue(order.name)
        self.assertEqual(order.partner_id, self.partner)
        self.assertEqual(order.stage_id, self.stage)
        self.assertEqual(order.priority_level, '2')
        self.assertIn(self.tag, order.tag_ids)

    def test_workflow_actions_and_duration(self):
        order = self.env['fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test workflow',
            'responsible_id': self.employee.id,
        })

        order.action_start_work()
        self.assertTrue(order.date_start)
        with self.assertRaises(UserError):
            order.action_start_work()

        order.date_start = fields.Datetime.now() - timedelta(hours=2)
        order.action_finish_work()
        self.assertTrue(order.date_end)
        self.assertGreater(order.duration, 0)
        with self.assertRaises(UserError):
            order.action_finish_work()

    def test_sale_order_creation_links_back_to_fsm_order(self):
        order = self.env['fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test sale order',
        })

        result = order.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(result['res_id'])

        self.assertEqual(sale_order.fsm_order_id, order)
        self.assertIn(sale_order, order.sale_order_ids)
        self.assertEqual(order.sale_count, 1)

    def test_stage_expansion(self):
        stages = self.env['fsm.order']._read_group_stage_ids(self.env['fsm.stage'], [], 'sequence')
        self.assertIn(self.stage, stages)
