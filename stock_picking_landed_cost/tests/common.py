# -*- coding: utf-8 -*-

from odoo import tools
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.modules.module import get_module_resource


class TestStockLandedCostsCommon(AccountingTestCase):

    def setUp(self):
        super(TestStockLandedCostsCommon, self).setUp()
        # Objects
        self.Product = self.env['product.product']
        self.Picking = self.env['stock.picking']
        self.Move = self.env['stock.move']
        self.LandedCost = self.env['stock.landed.cost']
        self.CostLine = self.env['stock.landed.cost.lines']
        self.StockQuant = self.env['stock.quant']
        self.StockInventory = self.env['stock.inventory']
        self.PurchaseOrder = self.env['purchase.order']

        # References
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.supplier_id = self.ref('base.res_partner_2')
        self.customer_id = self.ref('base.res_partner_4')
        self.picking_type_in_id = self.ref('stock.picking_type_in')
        self.picking_type_out_id = self.ref('stock.picking_type_out')
        self.supplier_location_id = self.ref('stock.stock_location_suppliers')
        self.stock_location_id = self.ref('stock.stock_location_stock')
        self.customer_location_id = self.ref('stock.stock_location_customers')
        self.categ_all = self.env.ref('product.product_category_all')

        # Create account
        self.default_account = self.env['account.account'].create({
            'name': "Purchased Stocks",
            'code': "X1101",
            'user_type_id': self.env['account.account.type'].create({
                    'name': 'Expenses',
                    'type': 'other'}).id,
            'reconcile': True})
        self.expenses_journal = self.env['account.journal'].create({
            'name': 'Expenses - Test',
            'code': 'TEXJ',
            'type': 'purchase',
            'default_debit_account_id': self.default_account.id,
            'default_credit_account_id': self.default_account.id})

        # Create product
        self.product1 = self.Product.create({
            'name': 'Product 1',
            'type': 'product',
            'cost_method': 'average',
            'valuation': 'real_time',
            'standard_price': 10,
            'lst_price': 20})
