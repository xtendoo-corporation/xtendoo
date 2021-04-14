# Copyright 2021 Manuel Calero Solís (http://www.xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common


class TestSaleOrderWeight(common.TransactionCase):

    def setUp(self):
        super(TestSaleOrderWeight, self).setUp()
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.env.ref('product.product_order_01')
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.sale_order_line_1 = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
        })

    def test_sale_order_weight(self):
        print("*"*80)
        self.sale_order.action_confirm()
        self.assertEqual(self.total_weight, 10.0)

