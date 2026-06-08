from odoo.tests import TransactionCase, tagged

@tagged("post_install", "-at_install")
class TestAggregatedInternalTransfers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id

        cls.product_1 = cls.env["product.product"].create({
            "name": "Product 1",
            "barcode": "PROD-1",
            "is_storable": True,
        })
        cls.product_2 = cls.env["product.product"].create({
            "name": "Product 2",
            "barcode": "PROD-2",
            "is_storable": True,
        })

        # Create two internal pickings from the same stock location
        cls.picking_1 = cls.env["stock.picking"].create({
            "picking_type_id": cls.warehouse.int_type_id.id,
            "location_id": cls.stock_location.id,
            "location_dest_id": cls.warehouse.wh_input_stock_loc_id.id,
            "move_ids": [
                (0, 0, {
                    'name': 'Move 1',
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 10,
                    'location_id': cls.stock_location.id,
                    'location_dest_id': cls.warehouse.wh_input_stock_loc_id.id,
                })
            ]
        })
        cls.picking_1.action_confirm()

        cls.picking_2 = cls.env["stock.picking"].create({
            "picking_type_id": cls.warehouse.int_type_id.id,
            "location_id": cls.stock_location.id,
            "location_dest_id": cls.warehouse.wh_input_stock_loc_id.id,
            "move_ids": [
                (0, 0, {
                    'name': 'Move 2',
                    'product_id': cls.product_1.id,
                    'product_uom_qty': 5,
                    'location_id': cls.stock_location.id,
                    'location_dest_id': cls.warehouse.wh_input_stock_loc_id.id,
                }),
                (0, 0, {
                    'name': 'Move 3',
                    'product_id': cls.product_2.id,
                    'product_uom_qty': 20,
                    'location_id': cls.stock_location.id,
                    'location_dest_id': cls.warehouse.wh_input_stock_loc_id.id,
                })
            ]
        })
        cls.picking_2.action_confirm()

    def test_aggregated_data_retrieval(self):
        """Test that data is correctly aggregated for the location."""
        data = self.env['stock.picking'].action_xt_get_aggregated_barcode_data(self.stock_location.id)

        lines = data['lines']
        self.assertEqual(len(lines), 2, "Should have 2 aggregated lines (one per product)")

        prod_1_line = next(l for l in lines if l['product_id'] == self.product_1.id)
        self.assertEqual(prod_1_line['qty_demand'], 15, "Total demand for Product 1 should be 10 + 5 = 15")

        prod_2_line = next(l for l in lines if l['product_id'] == self.product_2.id)
        self.assertEqual(prod_2_line['qty_demand'], 20, "Total demand for Product 2 should be 20")

    def test_aggregated_barcode_scan(self):
        """Test scanning a barcode in aggregated mode."""
        # Scan Product 1
        result = self.env['stock.picking'].action_xt_process_aggregated_barcode_scan(self.stock_location.id, "PROD-1")
        self.assertTrue(result['success'])

        # Check that Product 1 was scanned in picking_1 (due to FIFO priority in logic)
        self.assertEqual(self.picking_1.move_ids[0].xt_barcode_scanned_qty, 1)
        self.assertEqual(self.picking_2.move_ids.filtered(lambda m: m.product_id == self.product_1).xt_barcode_scanned_qty, 0)

        # Scan again enough to fill picking_1 and start picking_2
        for _ in range(10):
            self.env['stock.picking'].action_xt_process_aggregated_barcode_scan(self.stock_location.id, "PROD-1")

        self.assertEqual(self.picking_1.move_ids[0].xt_barcode_scanned_qty, 10, "Picking 1 move should be full")
        self.assertEqual(self.picking_2.move_ids.filtered(lambda m: m.product_id == self.product_1).xt_barcode_scanned_qty, 1, "Picking 2 move should have 1")

    def test_aggregated_complete_line(self):
        """Test completing an aggregated line."""
        data = self.env['stock.picking'].action_xt_get_aggregated_barcode_data(self.stock_location.id)
        prod_1_line = next(l for l in data['lines'] if l['product_id'] == self.product_1.id)

        self.env['stock.picking'].action_xt_complete_aggregated_line(prod_1_line['move_ids'])

        self.assertEqual(self.picking_1.move_ids[0].xt_barcode_scanned_qty, 10)
        self.assertEqual(self.picking_2.move_ids.filtered(lambda m: m.product_id == self.product_1).xt_barcode_scanned_qty, 5)

    def test_aggregated_validate(self):
        """Test validating all aggregated pickings."""
        # Fill everything
        self.env['stock.picking'].action_xt_complete_aggregated_line(self.picking_1.move_ids.ids + self.picking_2.move_ids.ids)

        self.env['stock.picking'].action_xt_validate_aggregated_pickings(self.stock_location.id)

        self.assertEqual(self.picking_1.state, 'done')
        self.assertEqual(self.picking_2.state, 'done')

    def test_aggregated_backorder_flow(self):
        """Test the partial validation flow (backorders) in aggregated mode."""
        # Scaneamos 5 de 10 de Product 1 (que están en picking_1)
        for _ in range(5):
            self.env['stock.picking'].action_xt_process_aggregated_barcode_scan(self.stock_location.id, "PROD-1")

        # Intentamos validar. Debería devolver la acción del wizard para picking_1
        res = self.env['stock.picking'].action_xt_validate_aggregated_pickings(self.stock_location.id)

        self.assertTrue(res.get('action'))
        self.assertEqual(res['action']['res_model'], 'stock.backorder.confirmation')

        # Simulamos que el usuario confirma el wizard (Crear Backorder)
        wizard = self.env['stock.backorder.confirmation'].with_context(res['action']['context']).create({})
        wizard.process()

        # picking_1 debe estar hecho (parcialmente) y debe existir un backorder
        self.assertEqual(self.picking_1.state, 'done')
        backorder = self.env['stock.picking'].search([('backorder_id', '=', self.picking_1.id)])
        self.assertTrue(backorder)
        self.assertEqual(backorder.move_ids[0].product_uom_qty, 5)

        # Volvemos a validar para procesar el resto (picking_2 no tiene nada escaneado, no debería procesarse)
        # Scanenamos Product 2 (20 unidades en picking_2) -> Scaneamos solo 10
        for _ in range(10):
            self.env['stock.picking'].action_xt_process_aggregated_barcode_scan(self.stock_location.id, "PROD-2")

        res2 = self.env['stock.picking'].action_xt_validate_aggregated_pickings(self.stock_location.id)
        self.assertTrue(res2.get('action'))
        self.assertEqual(res2['action']['res_model'], 'stock.backorder.confirmation')

        # Confirmamos backorder para picking_2
        wizard2 = self.env['stock.backorder.confirmation'].with_context(res2['action']['context']).create({})
        wizard2.process()

        self.assertEqual(self.picking_2.state, 'done')
        self.assertTrue(self.env['stock.picking'].search([('backorder_id', '=', self.picking_2.id)]))

    def test_aggregated_reset_and_adjust(self):
        """Test reset and manual quantity adjustments."""
        # Scan 5 units of Product 1
        for _ in range(5):
            self.env['stock.picking'].action_xt_process_aggregated_barcode_scan(self.stock_location.id, "PROD-1")

        data = self.env['stock.picking'].action_xt_get_aggregated_barcode_data(self.stock_location.id)
        prod_1_line = next(l for l in data['lines'] if l['product_id'] == self.product_1.id)

        # Reset
        self.env['stock.picking'].action_xt_reset_aggregated_line(prod_1_line['move_ids'])
        self.assertEqual(self.picking_1.move_ids[0].xt_barcode_scanned_qty, 0)

        # Manual Adjust +1
        self.env['stock.picking'].action_xt_add_aggregated_qty(prod_1_line['move_ids'], 1)
        self.assertEqual(self.picking_1.move_ids[0].xt_barcode_scanned_qty, 1)

        # Manual Adjust -1
        self.env['stock.picking'].action_xt_add_aggregated_qty(prod_1_line['move_ids'], -1)
        self.assertEqual(self.picking_1.move_ids[0].xt_barcode_scanned_qty, 0)
