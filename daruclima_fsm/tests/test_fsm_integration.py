# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import TransactionCase
from odoo.exceptions import UserError


class TestFSMIntegration(TransactionCase):
    """Test cases for FSM integration with other modules"""

    def setUp(self):
        super(TestFSMIntegration, self).setUp()

        # Create test data
        self.partner = self.env['res.partner'].create({
            'name': 'Integration Test Customer',
            'email': 'integration@test.com',
            'is_company': True,
        })

        self.employee = self.env['hr.employee'].create({
            'name': 'Integration Test Technician',
        })

        self.stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Integration Test Stage',
            'code': 'integration',
            'sequence': 1,
            'is_default': True,
        })

        self.product = self.env['product.product'].create({
            'name': 'Test Service Product',
            'type': 'service',
            'standard_price': 100.0,
            'list_price': 150.0,
        })

    def test_sale_order_integration(self):
        """Test integration with sale orders"""
        # Create FSM order
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Integration test with sales',
            'responsible_id': self.employee.id,
        })

        # Initially no sale order
        self.assertFalse(fsm_order.sale_order_id)
        self.assertEqual(fsm_order.quotation_count, 0)

        # Create quotation from FSM order
        result = fsm_order.action_create_quotation()

        # Verify sale order creation
        self.assertTrue(fsm_order.sale_order_id)
        self.assertEqual(fsm_order.sale_order_id.partner_id, self.partner)
        self.assertEqual(fsm_order.sale_order_id.origin, fsm_order.name)

        # Verify quotation count
        self.assertTrue(fsm_order.quotation_count >= 1)

        # Test viewing quotations
        view_result = fsm_order.action_view_quotations()
        self.assertEqual(view_result['res_model'], 'sale.order')

    def test_repair_order_integration(self):
        """Test integration with repair orders"""
        # Create FSM order
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Integration test with repairs',
            'responsible_id': self.employee.id,
        })

        # Initially no repair order
        self.assertFalse(fsm_order.repair_order_id)
        self.assertEqual(fsm_order.repair_count, 0)

        # Create repair from FSM order
        result = fsm_order.action_create_repair()

        # Verify repair order creation
        self.assertTrue(fsm_order.repair_order_id)
        self.assertEqual(fsm_order.repair_order_id.partner_id, self.partner)
        self.assertIn(fsm_order.name, fsm_order.repair_order_id.description)

        # Verify repair count
        self.assertEqual(fsm_order.repair_count, 1)

        # Test viewing repairs
        view_result = fsm_order.action_view_repairs()
        self.assertEqual(view_result['res_model'], 'repair.order')
        self.assertEqual(view_result['res_id'], fsm_order.repair_order_id.id)

    def test_hr_employee_integration(self):
        """Test integration with HR employees"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'HR integration test',
            'responsible_id': self.employee.id,
            'person_ids': [(6, 0, [self.employee.id])],
        })

        # Test technician assignment
        self.assertEqual(fsm_order.responsible_id, self.employee)
        self.assertIn(self.employee, fsm_order.person_ids)

    def test_totals_calculation(self):
        """Test totals calculation with sale orders"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Totals calculation test',
        })

        # Create sale order
        fsm_order.action_create_quotation()
        sale_order = fsm_order.sale_order_id

        # Add product line to sale order
        sale_order.order_line = [(0, 0, {
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'price_unit': self.product.list_price,
        })]

        # Trigger totals calculation
        fsm_order._compute_totals()

        # Verify calculations
        expected_sale_total = self.product.list_price * 2  # 150 * 2 = 300
        expected_cost_total = self.product.standard_price * 2  # 100 * 2 = 200
        expected_margin = expected_sale_total - expected_cost_total  # 300 - 200 = 100

        self.assertEqual(fsm_order.total_sale, expected_sale_total)
        self.assertEqual(fsm_order.total_cost, expected_cost_total)
        self.assertEqual(fsm_order.margin, expected_margin)
        self.assertAlmostEqual(fsm_order.margin_percent, 33.33, places=1)

    def test_invoice_status_integration(self):
        """Test invoice status integration with sale orders"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Invoice status test',
        })

        # Initially no invoice status
        self.assertEqual(fsm_order.invoice_status, 'no')

        # Create and confirm sale order
        fsm_order.action_create_quotation()
        sale_order = fsm_order.sale_order_id
        sale_order.action_confirm()

        # Check invoice status propagation
        fsm_order._compute_invoice_status()
        self.assertEqual(fsm_order.invoice_status, sale_order.invoice_status)

    def test_portal_integration(self):
        """Test portal access functionality"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Portal access test',
        })

        # Test access URL generation
        expected_url = f'/my/fsm/{fsm_order.id}'
        self.assertEqual(fsm_order.access_url, expected_url)

    def test_mail_integration(self):
        """Test mail thread integration"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Mail integration test',
        })

        # Test that FSM order inherits mail functionality
        self.assertTrue(hasattr(fsm_order, 'message_post'))
        self.assertTrue(hasattr(fsm_order, 'message_ids'))
        self.assertTrue(hasattr(fsm_order, 'activity_ids'))

        # Test posting a message
        message = fsm_order.message_post(
            body='Test message for FSM order',
            subject='Test Subject'
        )

        self.assertTrue(message)
        self.assertIn(message, fsm_order.message_ids)

    def test_workflow_integration(self):
        """Test complete workflow integration"""
        # Create complete FSM order
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'description': 'Complete workflow test',
            'responsible_id': self.employee.id,
        })

        # 1. Start work
        fsm_order.action_start_work()
        self.assertTrue(fsm_order.date_start)

        # 2. Create quotation
        fsm_order.action_create_quotation()
        self.assertTrue(fsm_order.sale_order_id)

        # 3. Create repair
        fsm_order.action_create_repair()
        self.assertTrue(fsm_order.repair_order_id)

        # 4. Finish work
        fsm_order.action_finish_work()
        self.assertTrue(fsm_order.date_end)

        # Verify all integrations work together
        self.assertTrue(fsm_order.duration > 0)
        self.assertEqual(fsm_order.quotation_count, 1)
        self.assertEqual(fsm_order.repair_count, 1)
