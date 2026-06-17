from odoo import fields
from odoo.fields import Command
from odoo.tests import TransactionCase


class TestSaleOrderEditDate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.res_partner_1")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Sale Order Edit Date",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 100.0,
                "taxes_id": [Command.clear()],
            }
        )

    @classmethod
    def _create_order(cls, date_order=None):
        order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "date_order": date_order or fields.Datetime.now(),
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 1.0,
                        }
                    )
                ],
            }
        )
        return order

    def test_action_confirm_preserves_existing_date_order(self):
        initial_date = fields.Datetime.to_datetime("2024-01-15 10:30:00")
        updated_date = fields.Datetime.to_datetime("2024-02-20 08:45:00")
        order = self._create_order(date_order=initial_date)

        order.action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertEqual(order.date_order, initial_date)

        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        order.date_order = updated_date

        order.action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertEqual(order.date_order, updated_date)

    def test_action_confirm_sets_date_order_when_empty(self):
        order = self._create_order()
        order.date_order = False
        before_confirm = fields.Datetime.now()

        order.action_confirm()

        after_confirm = fields.Datetime.now()
        self.assertEqual(order.state, "sale")
        self.assertTrue(order.date_order)
        self.assertGreaterEqual(order.date_order, before_confirm)
        self.assertLessEqual(order.date_order, after_confirm)

    def test_action_confirm_handles_mixed_recordsets(self):
        preserved_date = fields.Datetime.to_datetime("2024-03-10 09:15:00")
        order_with_date = self._create_order(date_order=preserved_date)
        order_without_date = self._create_order()
        order_without_date.date_order = False
        before_confirm = fields.Datetime.now()

        (order_with_date | order_without_date).action_confirm()

        after_confirm = fields.Datetime.now()
        self.assertEqual(order_with_date.state, "sale")
        self.assertEqual(order_with_date.date_order, preserved_date)
        self.assertEqual(order_without_date.state, "sale")
        self.assertTrue(order_without_date.date_order)
        self.assertGreaterEqual(order_without_date.date_order, before_confirm)
        self.assertLessEqual(order_without_date.date_order, after_confirm)
