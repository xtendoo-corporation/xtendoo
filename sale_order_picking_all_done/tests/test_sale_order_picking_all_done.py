# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestSaleOrderPickingAllDone(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente entrega y factura test"}
        )
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.income_account = cls.env["account.account"].search(
            [("account_type", "=", "income")],
            limit=1,
        )

    def _create_stockable_product(self, name, tracking="lot", price=10.0):
        product = self.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "tracking": tracking,
                "invoice_policy": "delivery",
                "list_price": price,
                "taxes_id": [(5, 0, 0)],
            }
        )
        if self.income_account:
            product.property_account_income_id = self.income_account
        return product

    def _create_lot(self, product, name):
        return self.env["stock.lot"].create(
            {
                "name": name,
                "product_id": product.id,
                "company_id": self.env.company.id,
            }
        )

    def _update_stock_quantity(self, product, lot, quantity):
        self.env["stock.quant"]._update_available_quantity(
            product,
            self.stock_location,
            lot_id=lot,
            quantity=quantity,
        )

    def _create_sale_order(self, line_values):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": quantity,
                            "price_unit": price,
                            "lot_id": lot.id,
                        }
                    )
                    for product, lot, quantity, price in line_values
                ],
            }
        )

    def _assert_line_delivered_with_lot(self, line, lot, quantity):
        self.assertAlmostEqual(line.qty_delivered, quantity)
        self.assertEqual(len(line.move_ids), 1)
        move = line.move_ids
        self.assertEqual(move.state, "done")
        self.assertEqual(move.restrict_lot_id, lot)
        self.assertEqual(move.move_line_ids.lot_id, lot)
        self.assertAlmostEqual(sum(move.move_line_ids.mapped("quantity")), quantity)

    def test_01_confirm_and_delivery_uses_order_quantity_and_lot(self):
        product = self._create_stockable_product("Producto lote entregable")
        lot = self._create_lot(product, "LOT-DELIVERY-01")
        self._update_stock_quantity(product, lot, 2.0)
        order = self._create_sale_order([(product, lot, 2.0, 15.0)])

        result = order.action_sale_order_confirm_and_delivery()

        self.assertTrue(result)
        self.assertEqual(order.state, "sale")
        self.assertTrue(order.picking_ids)
        self.assertTrue(all(picking.state == "done" for picking in order.picking_ids))
        self._assert_line_delivered_with_lot(order.order_line, lot, 2.0)
        self.assertFalse(order.invoice_ids)

    def test_02_confirm_delivery_invoice_posts_invoice(self):
        product = self._create_stockable_product("Producto lote facturable", price=20.0)
        lot = self._create_lot(product, "LOT-INVOICE-01")
        self._update_stock_quantity(product, lot, 3.0)
        order = self._create_sale_order([(product, lot, 3.0, 20.0)])

        action = order.action_sale_order_confirm_and_invoice()

        invoice = order.invoice_ids
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == product
        )
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(order.state, "sale")
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "posted")
        self.assertAlmostEqual(invoice_line.quantity, 3.0)
        self.assertEqual(order.invoice_status, "invoiced")
        self._assert_line_delivered_with_lot(order.order_line, lot, 3.0)

    def test_03_confirmed_order_delivers_two_lots_and_posts_one_invoice(self):
        product = self._create_stockable_product("Producto dos lotes", price=7.0)
        lot_a = self._create_lot(product, "LOT-MULTI-A")
        lot_b = self._create_lot(product, "LOT-MULTI-B")
        self._update_stock_quantity(product, lot_a, 1.0)
        self._update_stock_quantity(product, lot_b, 2.0)
        order = self._create_sale_order(
            [
                (product, lot_a, 1.0, 7.0),
                (product, lot_b, 2.0, 7.0),
            ]
        )
        order.action_confirm()

        action = order.action_sale_order_delivery_and_invoiced()

        invoice = order.invoice_ids
        invoice_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == product
        )
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "posted")
        self.assertAlmostEqual(sum(invoice_lines.mapped("quantity")), 3.0)
        self._assert_line_delivered_with_lot(order.order_line[0], lot_a, 1.0)
        self._assert_line_delivered_with_lot(order.order_line[1], lot_b, 2.0)

    def test_04_reexecution_does_not_duplicate_posted_invoice(self):
        product = self._create_stockable_product("Producto idempotente", price=11.0)
        lot = self._create_lot(product, "LOT-IDEMPOTENT-01")
        self._update_stock_quantity(product, lot, 1.0)
        order = self._create_sale_order([(product, lot, 1.0, 11.0)])

        order.action_sale_order_confirm_and_invoice()
        first_invoice = order.invoice_ids
        order.action_sale_order_confirm_and_invoice()

        self.assertEqual(order.invoice_ids, first_invoice)
        self.assertEqual(len(order.invoice_ids), 1)
        self.assertEqual(order.invoice_ids.state, "posted")
