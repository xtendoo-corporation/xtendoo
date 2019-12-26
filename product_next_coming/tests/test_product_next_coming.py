# Copyright 2019 Xtendoo - Manuel Calero Solis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# docker-compose run web --test-enable --stop-after-init -d test_db -i product_next_coming

from odoo.tests.common import HttpCase, tagged
from odoo import fields


class TestProductNextComing(HttpCase):
    
    def setUp(self):
        super(TestProductNextComing, self).setUp()

        self.datetime_now = fields.Datetime.now()

        self.partner = self.env['res.partner'].create({
            "name": "Test partner",
            "supplier": True,
            "is_company": True,
        })

        self.template = self.env['product.template'].create({
            'name': 'Product for test',
            'default_code': '001',
            'type': 'product',
        })

        self.product = self.env['product.product'].create({
            'product_tmpl_id': self.template.id,
            'standard_price': '1000',
        })

        self.purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'price_unit': 10,
                'date_planned': self.datetime_now})]
        })
        self.purchase_order_line = self.purchase_order.order_line
        self.purchase_order.button_confirm()

    def test_assert_product_created(self):
        self.assertNotEqual(self.product.id, 0)
        self.assertEqual(self.purchase_order_line.date_planned, self.datetime_now)
        self.assertEqual(self.product.date_next_coming, self.datetime_now)
