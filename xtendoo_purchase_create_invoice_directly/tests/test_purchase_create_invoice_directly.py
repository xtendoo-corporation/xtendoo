from odoo.tests.common import TransactionCase

class TestPurchaseCreateInvoiceDirectly(TransactionCase):
    def setUp(self):
        super().setUp()
        self.PurchaseOrder = self.env['purchase.order']
        self.Product = self.env['product.product']
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.Product.create({
            'name': 'Test Product',
            'type': 'product',
            'purchase_ok': True,
            'list_price': 10.0,
            'standard_price': 5.0,
        })

    def test_action_confirm_receive_invoice(self):
        order = self.PurchaseOrder.create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': 'Test Product',
                    'product_qty': 2,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 10.0,
                })
            ]
        })
        self.assertEqual(order.state, 'draft')
        order.action_confirm_receive_invoice()
        self.assertEqual(order.state, 'purchase')
        self.assertTrue(order.picking_ids)
        for picking in order.picking_ids:
            self.assertEqual(picking.state, 'done')
        self.assertTrue(order.invoice_ids)
        for invoice in order.invoice_ids:
            self.assertEqual(invoice.invoice_date, order.date_order.date())

