# -*- coding: utf-8 -*-

# Copyright 2019 Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
#
# docker-compose run web --test-enable --stop-after-init --addons-path /mnt/extra-addons -d hostelero -i test_picking_change_price --test-tags=test_picking_change_price
#

from odoo.tests.common import TransactionCase, tagged
import logging


class TestPickingChangePrice(TransactionCase):

    @classmethod
    def setUp(cls):
        super(TestPickingChangePrice, cls).setUp()

        logging.info("*"*80)

        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'default_code': 'prda',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.product_b = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'default_code': 'prdb',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.product_c = cls.env['product.product'].create({
            'name': 'Product C',
            'type': 'product',
            'default_code': 'prdc',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

    def test_product_created(self):
        """ This method test that product A, B and C was created.
        """

        logging.info("*"*80)

        self.assertEqual(self.product_a.name, 'Product A')
        self.assertEqual(self.product_b.name, 'Product X')
        self.assertEqual(self.product_c.name, 'Product C')
