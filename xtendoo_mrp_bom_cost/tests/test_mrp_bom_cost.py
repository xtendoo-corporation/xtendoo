# Copyright 2026 Xtendoo
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMrpBomCost(TransactionCase):
    def setUp(self):
        super().setUp()
        self.component = self.env["product.product"].create(
            {"name": "Component", "standard_price": 5.0}
        )
        self.finished = self.env["product.product"].create(
            {"name": "Finished product"}
        )
        self.bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "normal",
            }
        )
        self.line = self.env["mrp.bom.line"].create(
            {
                "bom_id": self.bom.id,
                "product_id": self.component.id,
                "product_qty": 3.0,
            }
        )

    def test_standard_price_related(self):
        self.assertEqual(self.line.standard_price, 5.0)

    def test_total_price_computed(self):
        self.assertEqual(self.line.total_price, 15.0)

    def test_total_price_recomputes_on_qty_change(self):
        self.line.product_qty = 4.0
        self.assertEqual(self.line.total_price, 20.0)

    def test_total_price_recomputes_on_standard_price_change(self):
        self.component.standard_price = 10.0
        self.assertEqual(self.line.total_price, 30.0)
