# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import TransactionCase
from odoo.exceptions import UserError


class TestFSMOrder(TransactionCase):
    """Test cases for FSM Order functionality"""

    def setUp(self):
        super(TestFSMOrder, self).setUp()

        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'is_company': True,
        })

        # Create delivery address
        self.delivery_address = self.env['res.partner'].create({
            'name': 'Delivery Address',
            'parent_id': self.partner.id,
            'type': 'delivery',
            'street': 'Test Street 123',
            'city': 'Test City',
        })

        # Create test employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Technician',
        })

        # Create test stage
        self.stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Test Stage',
            'code': 'test',
            'sequence': 1,
            'is_default': True,
            'is_closed': False,
            'color': '#FF0000',
        })

        # Create test tag
        self.tag = self.env['daruclima.fsm.tag'].create({
            'name': 'Test Tag',
            'color': 1,
        })

    def test_fsm_order_creation(self):
        """Test FSM order creation with default values"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test work order',
        })

        self.assertTrue(order.name)
        self.assertEqual(order.partner_id, self.partner)
        self.assertEqual(order.description, 'Test work order')
        self.assertEqual(order.stage_id, self.stage)
        self.assertEqual(order.priority, '2')
        self.assertFalse(order.is_closed)

    def test_fsm_order_sequence(self):
        """Test that FSM orders get proper sequence numbers"""
        order1 = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'First order',
        })

        order2 = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Second order',
        })

        self.assertNotEqual(order1.name, order2.name)
        self.assertNotEqual(order1.name, 'Nuevo')
        self.assertNotEqual(order2.name, 'Nuevo')

    def test_work_flow_actions(self):
        """Test work start and finish actions"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test workflow',
            'responsible_id': self.employee.id,
        })

        # Test starting work
        self.assertFalse(order.date_start)
        order.action_start_work()
        self.assertTrue(order.date_start)

        # Test that we can't start twice
        with self.assertRaises(UserError):
            order.action_start_work()

        # Test finishing work
        self.assertFalse(order.date_end)
        order.action_finish_work()
        self.assertTrue(order.date_end)

        # Test that we can't finish twice
        with self.assertRaises(UserError):
            order.action_finish_work()

    def test_duration_calculation(self):
        """Test duration calculation"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test duration',
        })

        # Initially no duration
        self.assertEqual(order.duration, 0.0)

        # Set start and end times
        from datetime import datetime, timedelta
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)

        order.write({
            'date_start': start_time,
            'date_end': end_time,
        })

        # Duration should be approximately 2 hours
        self.assertAlmostEqual(order.duration, 2.0, places=1)

    def test_quotation_creation(self):
        """Test quotation creation from FSM order"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test quotation creation',
        })

        self.assertFalse(order.sale_order_id)
        self.assertEqual(order.quotation_count, 0)

        # Create quotation
        result = order.action_create_quotation()

        self.assertTrue(order.sale_order_id)
        self.assertEqual(result['res_model'], 'sale.order')
        self.assertEqual(result['res_id'], order.sale_order_id.id)

        # Test that we can't create another quotation
        with self.assertRaises(UserError):
            order.action_create_quotation()

    def test_repair_creation(self):
        """Test repair order creation from FSM order"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test repair creation',
        })

        self.assertFalse(order.repair_order_id)
        self.assertEqual(order.repair_count, 0)

        # Create repair
        result = order.action_create_repair()

        self.assertTrue(order.repair_order_id)
        self.assertEqual(order.repair_count, 1)
        self.assertEqual(result['res_model'], 'repair.order')
        self.assertEqual(result['res_id'], order.repair_order_id.id)

        # Test that we can't create another repair
        with self.assertRaises(UserError):
            order.action_create_repair()

    def test_stage_expansion(self):
        """Test stage expansion for kanban view"""
        order_model = self.env['daruclima.fsm.order']

        # Test stage expansion method
        stages = order_model._read_group_stage_ids([], [])

        self.assertTrue(len(stages) > 0)
        self.assertIn(self.stage, stages)

    def test_portal_access(self):
        """Test portal access URL computation"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test portal access',
        })

        expected_url = f'/my/fsm/{order.id}'
        self.assertEqual(order.access_url, expected_url)

    def test_location_and_contact_domains(self):
        """Test that location and contact domains work correctly"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'location_id': self.delivery_address.id,
            'description': 'Test location',
        })

        self.assertEqual(order.location_id, self.delivery_address)
        self.assertEqual(order.location_id.parent_id, self.partner)

    def test_tags_functionality(self):
        """Test tags functionality"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test tags',
            'tag_ids': [(6, 0, [self.tag.id])],
        })

        self.assertIn(self.tag, order.tag_ids)

    def test_technician_assignment(self):
        """Test technician assignment"""
        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Test technician',
            'responsible_id': self.employee.id,
            'person_ids': [(6, 0, [self.employee.id])],
        })

        self.assertEqual(order.responsible_id, self.employee)
        self.assertIn(self.employee, order.person_ids)
