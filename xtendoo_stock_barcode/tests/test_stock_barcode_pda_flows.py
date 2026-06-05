from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

@tagged("post_install", "-at_install")
class TestStockBarcodePdaFlows(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.source_location = cls.warehouse.lot_stock_id
        cls.dest_location = cls.env["stock.location"].create(
            {
                "name": "Target Location",
                "location_id": cls.source_location.id,
                "barcode": "TARGET-LOC",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Regular Product",
                "barcode": "PROD-101",
                "is_storable": True,
            }
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.int_type_id.id,
                "location_id": cls.source_location.id,
                "location_dest_id": cls.source_location.id,
            }
        )

    def test_line_creation_auto_assigns_package_and_location(self):
        # Allow extra product
        self.picking.picking_type_id.xt_barcode_allow_extra_product = True
        
        # Set context variables
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location
        
        package = self.env["stock.package"].create({"name": "PACK-100"})
        self.picking.xt_barcode_current_package_id = package
        
        # Scan product to create line
        self.picking.action_scan_barcode("PROD-101")
        
        line = self.picking.xt_barcode_current_line_id
        self.assertTrue(line)
        self.assertEqual(line.location_dest_id, self.dest_location)
        self.assertEqual(line.result_package_id, package)
        self.assertTrue(line.xt_barcode_package_scanned)
