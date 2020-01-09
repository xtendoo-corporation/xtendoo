# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
#
# docker-compose run web --test-enable --stop-after-init -d test_db -i sale_campaign
#

from odoo.tests import common


class TestSalePromotion(common.TransactionCase):

    def setUp(self):
        super(TestSalePromotion, self).setUp()

        self.partner = self.env.ref('base.res_partner_1')
        self.partner_exclude = self.env.ref('base.res_partner_2')
        self.pricelist = self.env.ref('product.list0')

    def test_01_product_price(self):
        product_product_1 = self.env.ref('product.product_product_1')
        order_line_values = {
            'name': product_product_1.name,
            'product_id': product_product_1.id,
            'product_uom_qty': 1,
            'product_uom': product_product_1.uom_id.id,
            'price_unit': product_product_1.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].price_unit, 30.75)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].price_unit, 27.5)

    def test_02_variant_price(self):
        product_product_2 = self.env.ref('product.product_product_2')
        order_line_values = {
            'name': product_product_2.name,
            'product_id': product_product_2.id,
            'product_uom_qty': 1,
            'product_uom': product_product_2.uom_id.id,
            'price_unit': product_product_2.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].price_unit, 38.25)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].price_unit, 34.99)

    def test_03_category_price(self):
        expense_product_product_template = self.env.ref(
            'product.expense_product_product_template')
        order_line_values = {
            'name': expense_product_product_template.name,
            'product_id': expense_product_product_template.id,
            'product_uom_qty': 1,
            'product_uom': expense_product_product_template.uom_id.id,
            'price_unit': expense_product_product_template.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].price_unit, 14)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].price_unit, 10)

    def test_04_product_discount(self):
        product_product_3 = self.env.ref('product.product_product_3')
        order_line_values = {
            'name': product_product_3.name,
            'product_id': product_product_3.id,
            'product_uom_qty': 1,
            'product_uom': product_product_3.uom_id.id,
            'price_unit': product_product_3.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 10)

    def test_05_variant_discount(self):

        product_product_4 = self.env.ref('product.product_product_4')
        order_line_values = {
            'name': product_product_4.name,
            'product_id': product_product_4.id,
            'product_uom_qty': 1,
            'product_uom': product_product_4.uom_id.id,
            'price_unit': product_product_4.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 20)

    def test_06_category_discount(self):
        expense_hotel_product_template = self.env.ref(
            'product.expense_hotel_product_template')
        order_line_values = {
            'name': expense_hotel_product_template.name,
            'product_id': expense_hotel_product_template.id,
            'product_uom_qty': 1,
            'product_uom': expense_hotel_product_template.uom_id.id,
            'price_unit': expense_hotel_product_template.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 20)

    # def test_07_product_add(self):
    #     product_product_5 = self.env.ref(
    #         'product.product_product_5')
    #     order_line_values = {
    #         'name': product_product_5.name,
    #         'product_id': product_product_5.id,
    #         'product_uom_qty': 1,
    #         'product_uom': product_product_5.uom_id.id,
    #         'price_unit': product_product_5.list_price,
    #     }
    #     order = self.env['sale.order'].create({
    #         'partner_id': self.partner.id,
    #         'partner_invoice_id': self.partner.id,
    #         'partner_shipping_id': self.partner.id,
    #         'order_line': [(0, 0, order_line_values)],
    #         'pricelist_id': self.pricelist.id,
    #     })
    #     original_order_line = order.order_line[0]
    #     self.assertEqual(len(order.order_line), 1)
    #     order.apply_promotions()
    #     self.assertEqual(len(order.order_line), 1)
    #
    #     original_order_line.product_uom_qty = 4
    #     order.apply_promotions()
    #     self.assertEqual(len(order.order_line), 2)
    #     new_line = order.order_line.filtered(
    #         lambda l: l.id != original_order_line.id)
    #     self.assertEqual(new_line.price_unit, 0)

    def test_08_category_discount_mixin(self):
        product_product_6 = self.env.ref(
            'product.product_product_6')
        promotion = self.env.ref(
            'sale_campaign.promotion_08'
        )
        order_line_6_values = {
            'name': product_product_6.name,
            'product_id': product_product_6.id,
            'product_uom_qty': 1,
            'product_uom': product_product_6.uom_id.id,
            'price_unit': product_product_6.list_price,
        }
        product_product_7 = self.env.ref(
            'product.product_product_7')
        order_line_7_values = {
            'name': product_product_7.name,
            'product_id': product_product_7.id,
            'product_uom_qty': 1,
            'product_uom': product_product_7.uom_id.id,
            'price_unit': product_product_7.list_price,
        }
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [
                (0, 0, order_line_6_values),
                (0, 0, order_line_7_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(len(order.order_line), 2)
        self.assertEqual(order.order_line[0].discount, 0)
        self.assertEqual(order.order_line[1].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 0)
        self.assertEqual(order.order_line[1].discount, 0)

        order.order_line[0].product_uom_qty = 5
        order.order_line[1].product_uom_qty = 5
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 0)
        self.assertEqual(order.order_line[1].discount, 0)

        promotion.mixing_allowed = True
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 20)
        self.assertEqual(order.order_line[1].discount, 20)

    def test_10_all_partners(self):
        product_product_8 = self.env.ref('product.product_product_8')
        order_line_values = {
            'name': product_product_8.name,
            'product_id': product_product_8.id,
            'product_uom_qty': 1,
            'product_uom': product_product_8.uom_id.id,
            'price_unit': product_product_8.list_price,
        }

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 20)

    def test_11_partner_exclude(self):
        product_product_9 = self.env.ref('product.product_product_9')
        order_line_values = {
            'name': product_product_9.name,
            'product_id': product_product_9.id,
            'product_uom_qty': 1,
            'product_uom': product_product_9.uom_id.id,
            'price_unit': product_product_9.list_price,
        }

        order = self.env['sale.order'].create({
            'partner_id': self.partner_exclude.id,
            'partner_invoice_id': self.partner_exclude.id,
            'partner_shipping_id': self.partner_exclude.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 0)

    def test_11_partner_include(self):
        product_product_9 = self.env.ref('product.product_product_9')
        order_line_values = {
            'name': product_product_9.name,
            'product_id': product_product_9.id,
            'product_uom_qty': 1,
            'product_uom': product_product_9.uom_id.id,
            'price_unit': product_product_9.list_price,
        }

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, order_line_values)],
            'pricelist_id': self.pricelist.id,
        })
        self.assertEqual(order.order_line[0].discount, 0)
        order.apply_promotions()
        self.assertEqual(order.order_line[0].discount, 15)
