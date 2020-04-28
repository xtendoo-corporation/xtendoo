# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.stock_barcodes.tests.test_stock_barcodes import\
    TestStockBarcodes


class TestStockBarcodesInternalTransfer(TestStockBarcodes):
    def setUp(self):
        super().setUp()
        self.ScanReadInternalTransfer = self.env['wiz.stock.barcodes.read.internal.transfer']
        self.stock_picking_model = self.env.ref('stock.model_stock_picking')

        # Model Data
        self.partner_agrolite = self.env.ref('base.res_partner_2')
        self.picking_type_in = self.env.ref('stock.picking_type_in')
        self.picking_type_out = self.env.ref('stock.picking_type_out')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.categ_kgm = self.env.ref('uom.product_uom_categ_kgm')

        self.picking_in_01 = self.env['stock.picking'].with_context(
            planned_picking=True
        ).create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': self.partner_agrolite.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.picking_in_01.action_confirm()
        vals = self.picking_in_01.action_barcode_scan()
        self.wiz_scan_internal_transfer = self.ScanReadInternalTransfer.with_context(
            vals['context']
        ).create({})

    def test_wiz_internal_transfer_values(self):
        self.assertEqual(self.wiz_scan_internal_transfer.location_id,
                         self.picking_in_01.location_dest_id)
        self.assertEqual(self.wiz_scan_internal_transfer.res_model_id,
                         self.stock_picking_model)
        self.assertEqual(self.wiz_scan_internal_transfer.res_id,
                         self.picking_in_01.id)
        self.assertEqual(self.wiz_scan_internal_transfer.display_name,
                         'Barcode reader - %s - OdooBot' % (
                             self.picking_in_01.name))

    def test_picking_wizard_scan_product(self):
        self.action_barcode_scanned(self.wiz_scan_internal_transfer, '8480000723208')
        self.assertEqual(
            self.wiz_scan_internal_transfer.product_id, self.product_wo_tracking)

