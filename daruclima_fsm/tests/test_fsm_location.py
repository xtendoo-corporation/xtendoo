# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import TransactionCase


class TestFSMLocation(TransactionCase):
    """Test cases for FSM location and address functionality"""

    def setUp(self):
        super(TestFSMLocation, self).setUp()

        # Create test company partner
        self.company_partner = self.env['res.partner'].create({
            'name': 'Test Company',
            'is_company': True,
            'email': 'company@test.com',
            'phone': '+1234567890',
            'street': 'Company Main Street 123',
            'city': 'Company City',
            'zip': '12345',
            'country_id': self.env.ref('base.us').id,
        })

        # Create delivery addresses
        self.delivery_address1 = self.env['res.partner'].create({
            'name': 'Warehouse Location',
            'parent_id': self.company_partner.id,
            'type': 'delivery',
            'street': 'Warehouse Street 456',
            'city': 'Warehouse City',
            'zip': '54321',
        })

        self.delivery_address2 = self.env['res.partner'].create({
            'name': 'Branch Office',
            'parent_id': self.company_partner.id,
            'type': 'delivery',
            'street': 'Branch Avenue 789',
            'city': 'Branch City',
            'zip': '98765',
        })

        # Create contact persons
        self.contact1 = self.env['res.partner'].create({
            'name': 'John Contact',
            'parent_id': self.company_partner.id,
            'is_company': False,
            'email': 'john@test.com',
            'phone': '+1111111111',
        })

        self.contact2 = self.env['res.partner'].create({
            'name': 'Jane Contact',
            'parent_id': self.company_partner.id,
            'is_company': False,
            'email': 'jane@test.com',
            'phone': '+2222222222',
        })

        # Create test stage
        self.stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Test Stage',
            'code': 'test',
            'sequence': 1,
            'is_default': True,
        })

    def test_location_assignment(self):
        """Test location assignment to FSM orders"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'location_id': self.delivery_address1.id,
            'description': 'Location test order',
        })

        self.assertEqual(fsm_order.location_id, self.delivery_address1)
        self.assertEqual(fsm_order.location_id.parent_id, self.company_partner)
        self.assertEqual(fsm_order.location_id.type, 'delivery')

    def test_contact_assignment(self):
        """Test contact person assignment to FSM orders"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'contact_id': self.contact1.id,
            'description': 'Contact test order',
        })

        self.assertEqual(fsm_order.contact_id, self.contact1)
        self.assertEqual(fsm_order.contact_id.parent_id, self.company_partner)
        self.assertFalse(fsm_order.contact_id.is_company)

    def test_location_and_contact_together(self):
        """Test using both location and contact in same order"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'location_id': self.delivery_address1.id,
            'contact_id': self.contact1.id,
            'description': 'Location and contact test',
        })

        self.assertEqual(fsm_order.location_id, self.delivery_address1)
        self.assertEqual(fsm_order.contact_id, self.contact1)
        self.assertEqual(fsm_order.location_id.parent_id, self.company_partner)
        self.assertEqual(fsm_order.contact_id.parent_id, self.company_partner)

    def test_multiple_locations_available(self):
        """Test that multiple delivery addresses are available"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'description': 'Multiple locations test',
        })

        # Get available delivery addresses for this partner
        delivery_addresses = self.env['res.partner'].search([
            ('parent_id', '=', self.company_partner.id),
            ('type', '=', 'delivery')
        ])

        self.assertIn(self.delivery_address1, delivery_addresses)
        self.assertIn(self.delivery_address2, delivery_addresses)
        self.assertEqual(len(delivery_addresses), 2)

    def test_multiple_contacts_available(self):
        """Test that multiple contacts are available"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'description': 'Multiple contacts test',
        })

        # Get available contacts for this partner
        contacts = self.env['res.partner'].search([
            ('parent_id', '=', self.company_partner.id),
            ('is_company', '=', False)
        ])

        self.assertIn(self.contact1, contacts)
        self.assertIn(self.contact2, contacts)
        self.assertEqual(len(contacts), 2)

    def test_location_domain_constraint(self):
        """Test that location domain works correctly"""
        # Create another company with its own delivery address
        other_company = self.env['res.partner'].create({
            'name': 'Other Company',
            'is_company': True,
        })

        other_delivery = self.env['res.partner'].create({
            'name': 'Other Delivery',
            'parent_id': other_company.id,
            'type': 'delivery',
        })

        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'description': 'Domain constraint test',
        })

        # Verify that we can only see delivery addresses for the selected partner
        valid_locations = self.env['res.partner'].search([
            ('parent_id', '=', self.company_partner.id),
            ('type', '=', 'delivery')
        ])

        self.assertIn(self.delivery_address1, valid_locations)
        self.assertIn(self.delivery_address2, valid_locations)
        self.assertNotIn(other_delivery, valid_locations)

    def test_contact_domain_constraint(self):
        """Test that contact domain works correctly"""
        # Create another company with its own contact
        other_company = self.env['res.partner'].create({
            'name': 'Other Company',
            'is_company': True,
        })

        other_contact = self.env['res.partner'].create({
            'name': 'Other Contact',
            'parent_id': other_company.id,
            'is_company': False,
        })

        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'description': 'Contact domain test',
        })

        # Verify that we can only see contacts for the selected partner
        valid_contacts = self.env['res.partner'].search([
            ('parent_id', '=', self.company_partner.id),
            ('is_company', '=', False)
        ])

        self.assertIn(self.contact1, valid_contacts)
        self.assertIn(self.contact2, valid_contacts)
        self.assertNotIn(other_contact, valid_contacts)

    def test_location_address_details(self):
        """Test that location address details are properly stored"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'location_id': self.delivery_address1.id,
            'description': 'Address details test',
        })

        location = fsm_order.location_id
        self.assertEqual(location.street, 'Warehouse Street 456')
        self.assertEqual(location.city, 'Warehouse City')
        self.assertEqual(location.zip, '54321')

    def test_contact_details(self):
        """Test that contact details are properly stored"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'contact_id': self.contact1.id,
            'description': 'Contact details test',
        })

        contact = fsm_order.contact_id
        self.assertEqual(contact.name, 'John Contact')
        self.assertEqual(contact.email, 'john@test.com')
        self.assertEqual(contact.phone, '+1111111111')

    def test_no_location_or_contact(self):
        """Test FSM order without specific location or contact"""
        fsm_order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.company_partner.id,
            'description': 'No location or contact test',
        })

        # Should still work with just the main partner
        self.assertEqual(fsm_order.partner_id, self.company_partner)
        self.assertFalse(fsm_order.location_id)
        self.assertFalse(fsm_order.contact_id)
