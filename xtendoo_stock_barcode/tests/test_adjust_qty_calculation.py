# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.tools.float_utils import float_compare

@tagged("post_install", "-at_install", "xtendoo_stock_barcode")
class TestStockBarcodeAdjustQtyCalculation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Picking = cls.env['stock.picking']
        cls.Product = cls.env['product.product']
        cls.Warehouse = cls.env['stock.warehouse']

        cls.warehouse = cls.Warehouse.search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.product = cls.Product.create({
            'name': 'Test Product Calculate',
            'type': 'product',
            'barcode': 'BC-CALC-001',
        })

        cls.picking = cls.Picking.create({
            'picking_type_id': cls.warehouse.out_type_id.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.move = cls.env['stock.move'].create({
            'name': 'Test Move Calculate',
            'picking_id': cls.picking.id,
            'product_id': cls.product.id,
            'product_uom': cls.product.uom_id.id,
            'product_uom_qty': 10.0,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })
        cls.picking.action_confirm()

    def test_adjust_qty_and_recalculation(self):
        """Validar que action_xt_adjust_qty actualiza correctamente el campo xt_barcode_scanned_qty"""
        move = self.move
        self.assertEqual(move.xt_barcode_scanned_qty, 0.0, "Debe empezar en 0")

        # Incrementar 5 unidades
        self.picking.action_xt_adjust_qty(move.id, 5.0)
        # Sincronizar campo computado si el test no lo hace automáticamente por el entorno
        move._compute_xt_barcode_checking()
        self.assertEqual(move.xt_barcode_scanned_qty, 5.0, "Debe tener 5 unidades escaneadas")

        # Incrementar 2 unidades más
        self.picking.action_xt_adjust_qty(move.id, 2.0)
        move._compute_xt_barcode_checking()
        self.assertEqual(move.xt_barcode_scanned_qty, 7.0, "Debe tener 7 unidades en total")

        # Restar 3 unidades
        self.picking.action_xt_adjust_qty(move.id, -3.0)
        move._compute_xt_barcode_checking()
        self.assertEqual(move.xt_barcode_scanned_qty, 4.0, "Debe tener 4 unidades tras restar")

        # Resetear línea
        self.picking.action_xt_reset_line(move.id)
        move._compute_xt_barcode_checking()
        self.assertEqual(move.xt_barcode_scanned_qty, 0.0, "Debe volver a 0 tras resetear")

    def test_complete_line_and_recalculation(self):
        """Validar que action_xt_complete_line actualiza correctamente el campo xt_barcode_scanned_qty"""
        move = self.move
        self.picking.action_xt_complete_line(move.id)
        move._compute_xt_barcode_checking()
        self.assertEqual(move.xt_barcode_scanned_qty, 10.0, "Debe estar completo (10 unidades)")
        self.assertEqual(move.xt_barcode_check_state, 'complete', "El estado debe ser completo")

