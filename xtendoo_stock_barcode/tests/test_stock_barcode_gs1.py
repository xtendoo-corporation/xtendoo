from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError
from odoo import Command

@tagged("post_install", "-at_install")
class TestStockBarcodeGs1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.write(
            {
                "group_ids": [
                    Command.link(cls.env.ref("stock.group_stock_multi_locations").id),
                    Command.link(cls.env.ref("stock.group_tracking_lot").id),
                    Command.link(cls.env.ref("stock.group_production_lot").id),
                    Command.link(cls.env.ref("uom.group_uom").id),
                ]
            }
        )
        
        # Ensure company uses GS1
        cls.env.company.nomenclature_id = cls.env.ref("barcodes_gs1_nomenclature.default_gs1_nomenclature")
        cls.parser = cls.env["barcode.gs1.parser"]
        
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.source_location = cls.warehouse.lot_stock_id
        cls.dest_location = cls.env["stock.location"].create(
            {
                "name": "GS1 Barcode Shelf",
                "location_id": cls.source_location.id,
                "barcode": "01BC-SHELF-GS1",
            }
        )
        
        cls.product_gtin = cls.env["product.product"].create({
            "name": "GS1 Product",
            "barcode": "15290000000007",
            "is_storable": True,
            "tracking": "lot",
        })
        
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.int_type_id.id,
                "location_id": cls.source_location.id,
                "location_dest_id": cls.source_location.id,
            }
        )

    def test_parse_gs1_barcode_returns_false_if_not_gs1(self):
        self.env.company.nomenclature_id = self.env.ref("barcodes.default_barcode_nomenclature")
        # Should return False when nomenclature is not GS1
        res = self.parser.parse_gs1_barcode("011529000000000010LOT123")
        self.assertFalse(res)

    def test_parse_gs1_barcode_extracts_product_and_lot(self):
        # GTIN (01) = 15290000000007, LOT (10) = LOT123, QTY (30) = 5
        barcode = "]C1011529000000000710LOT123\x1D305"
        res = self.parser.parse_gs1_barcode(barcode)
        self.assertTrue(res)
        self.assertEqual(res.get("product"), "15290000000007")
        self.assertEqual(res.get("lot"), "LOT123")
        self.assertEqual(res.get("product_qty"), 5.0)

    def test_scan_gs1_barcode_in_picking(self):
        # Enable extra product since this wasn't planned
        self.picking.picking_type_id.xt_barcode_allow_extra_product = True
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location
        
        # Simulating GTIN+Lot+Qty
        barcode = "]C1011529000000000710LOT123\x1D305"
        res = self.picking.action_scan_barcode(barcode)
        
        self.assertFalse(res)
        line = self.picking.xt_barcode_current_line_id
        self.assertTrue(line)
        self.assertEqual(line.product_id, self.product_gtin)
        self.assertEqual(line.quantity, 5.0)
        self.assertEqual(line.lot_name, "LOT123")
        self.assertTrue(line.xt_barcode_tracking_scanned)
