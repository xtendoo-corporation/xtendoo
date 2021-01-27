# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common
from datetime import datetime


class TestSaleOrderLineMarginPercent(common.TransactionCase):
    def setUp(self):
        super(TestSaleOrderLineMarginPercent, self).setUp()
        self.SaleOrder = self.env['sale.order']
        self.product_uom_id = self.ref('uom.product_uom_unit')
        self.pricelist_id = self.env["product.pricelist"].create(
            {
                "name": "Public Pricelist",
                "sequence": 1,
            }
        ).id
        self.partner_id = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.org",
                "is_company": True,
                "parent_id": False,
            }
        ).id
        self.partner_invoice_address_id = self.env["res.partner"].create(
            {
                "name": "Billy Fox",
                "parent_id": self.partner_id,
                "function": "Production Supervisor",
                "email": "billy.fox45@example.com",
                "phone": "(915)-498-5611",
            }
        ).id
        self.product_id = self.env["product.product"].create(
            {
                "name": "Individual Workplace",
                "type": "consu",
                "description_purchase": "Test Description",
                "default_code": "FURN_0789",
                "uom_id": self.product_uom_id,
                "uom_po_id": self.product_uom_id,
            }
        ).id

    def test_sale_margin(self):
        """ Test the sale_margin module in Odoo. """
        sale_order_so11 = self.SaleOrder.create({
            'date_order': datetime.today(),
            'name': 'Test_SO011',
            'order_line': [
                (0, 0, {
                    'name': '[CARD] Individual Workplace',
                    'purchase_price': 700.0,
                    'price_unit': 1000.0,
                    'product_uom': self.product_uom_id,
                    'product_uom_qty': 10.0,
                    'state': 'draft',
                    'product_id': self.product_id}),
                (0, 0, {
                    'name': 'Line without product_uom',
                    'price_unit': 1000.0,
                    'purchase_price': 700.0,
                    'product_uom_qty': 10.0,
                    'state': 'draft',
                    'product_id': self.product_id})],
            'partner_id': self.partner_id,
            'partner_invoice_id': self.partner_invoice_address_id,
            'partner_shipping_id': self.partner_invoice_address_id,
            'pricelist_id': self.pricelist_id})
        # Confirm the sales order.
        sale_order_so11.action_confirm()
        # Verify that margin field gets bind with the value.

        print("assertEqual ::::")

        self.assertEqual(sale_order_so11.margin, 6000.00, "Sales order margin should be 6000.00")
        sale_order_so11.order_line[1].purchase_price = 800
        self.assertEqual(sale_order_so11.margin, 5000.00, "Sales order margin should be 5000.00")

