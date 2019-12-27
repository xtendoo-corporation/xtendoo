# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from .common import TestStockLandedCostsCommon
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestStockLandedCostsAVCO(TestStockLandedCostsCommon):

    def test_stock_landed_costs_avco(self):
        # In order to test the landed costs feature of stock,
        # I create a landed cost, confirm it and check its account move created

        # make some stock
        self.StockQuant._update_available_quantity(self.product1, self.stock_location, 10)
        self.assertEqual(len(self.StockQuant._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(self.StockQuant._get_available_quantity(self.product1, self.stock_location), 10.0)

        # remove them with an inventory adjustment
        inventory = self.StockInventory.create({
            'name': 'initial',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 10)
        inventory.line_ids.product_qty = 100.0
        inventory.action_validate()

        # check
        self.assertEqual(self.StockQuant._get_available_quantity(self.product1, self.stock_location), 100.0)

        # purchase order
        po_vals = {
            'partner_id': self.env.ref('base.res_partner_1').id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 100.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 20.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
            }

        self.po = self.PurchaseOrder.create(po_vals)

        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.invoice_status, 'no', 'Purchase: PO invoice_status should be "Not purchased"')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')

        # picking
        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created')
        self.picking = self.po.picking_ids[0]
        self.picking.move_line_ids.write({'qty_done': 100.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [100.0], 'Purchase: all products should be received')

        # products
        self.assertEqual(self.product1.standard_price, 15.0, 'Product: standard price')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 200.0, 'Product: available stock quantity')

        # landed cost
        lc_vals = {
            'picking_ids': [(6, 0, [self.picking.id])],
            'account_journal_id': self.expenses_journal.id,
            'cost_lines': [
                (0, 0, {
                    'name': 'equal split',
                    'split_method': 'equal',
                    'price_unit': 30,
                    'product_id': self.product1.id,
                })],
            }

        self.lc = self.LandedCost.create(lc_vals)

        self.lc.compute_landed_cost()
        self.lc.button_validate()

        # if divide landed cost price between total units in stock 30 / 200
        self.assertEqual(self.product1.standard_price, 15.15, 'Product: standard price')