from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestXtendooStockBarcode(TransactionCase):
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
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.source_location = cls.warehouse.lot_stock_id
        cls.dest_location = cls.env["stock.location"].create(
            {
                "name": "Barcode Shelf",
                "location_id": cls.source_location.id,
                "barcode": "BC-SHELF-01",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Barcode Product",
                "barcode": "BC-PROD-01",
                "is_storable": True,
            }
        )
        cls.tracked_product = cls.env["product.product"].create(
            {
                "name": "Tracked Barcode Product",
                "barcode": "BC-PROD-LOT-01",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        cls.existing_lot = cls.env["stock.lot"].create(
            {
                "name": "LOT-EXIST-01",
                "product_id": cls.tracked_product.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.package = cls.env["stock.package"].create({"name": "PACK-MENU-01"})
        cls.warehouse.int_type_id.barcode = "BC-TYPE-INT-01"

    def setUp(self):
        super().setUp()
        self.picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.int_type_id.id,
                "location_id": self.source_location.id,
                "location_dest_id": self.source_location.id,
            }
        )

    def test_scan_source_location_sets_context(self):
        self.picking.action_xt_barcode_set_mode_source()
        self.picking.action_scan_barcode("BC-SHELF-01")
        self.assertEqual(self.picking.xt_barcode_source_location_id, self.dest_location)
        self.assertEqual(self.picking.xt_barcode_mode, "product")

    def test_scan_source_location_accepts_lowercase_barcode(self):
        self.picking.action_xt_barcode_set_mode_source()
        self.picking.action_scan_barcode("bc-shelf-01")
        self.assertEqual(self.picking.xt_barcode_source_location_id, self.dest_location)

    def test_scan_source_location_accepts_normalized_barcode_without_separators(self):
        self.picking.action_xt_barcode_set_mode_source()
        self.picking.action_scan_barcode("bcshelf01")
        self.assertEqual(self.picking.xt_barcode_source_location_id, self.dest_location)

    def test_scan_product_creates_and_increments_line(self):
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        self.picking.action_scan_barcode("BC-PROD-01")
        line = self.picking.xt_barcode_current_line_id
        self.assertTrue(line)
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.quantity, 1.0)

        self.picking.action_scan_barcode("BC-PROD-01")
        self.assertEqual(line.quantity, 2.0)
        self.assertTrue(line.xt_barcode_source_scanned)

    def test_scan_tracked_product_then_existing_lot(self):
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        self.picking.action_scan_barcode("BC-PROD-LOT-01")
        self.assertEqual(self.picking.xt_barcode_mode, "lot")
        line = self.picking.xt_barcode_current_line_id
        self.assertEqual(line.product_id, self.tracked_product)
        self.assertEqual(line.quantity, 1.0)

        self.picking.action_scan_barcode("LOT-EXIST-01")
        self.assertEqual(line.lot_id, self.existing_lot)
        self.assertTrue(line.xt_barcode_tracking_scanned)
        self.assertEqual(self.picking.xt_barcode_mode, "product")

    def test_scan_product_requires_source_when_mandatory(self):
        self.picking.picking_type_id.xt_barcode_restrict_scan_source_location = "mandatory"
        self.picking.xt_barcode_destination_location_id = self.dest_location

        with self.assertRaises(UserError):
            self.picking.action_scan_barcode("BC-PROD-01")

    def test_scan_product_disallows_extra_when_disabled(self):
        self.picking.picking_type_id.xt_barcode_allow_extra_product = False
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        with self.assertRaises(UserError):
            self.picking.action_scan_barcode("BC-PROD-01")

    def test_scan_product_requires_destination_after_product_when_mandatory(self):
        self.picking.picking_type_id.xt_barcode_restrict_scan_dest_location = "mandatory"
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        self.picking.action_scan_barcode("BC-PROD-01")
        line = self.picking.xt_barcode_current_line_id
        self.assertFalse(line.xt_barcode_destination_scanned)
        self.assertEqual(self.picking.xt_barcode_mode, "destination")

        self.picking.action_scan_barcode("BC-SHELF-01")
        self.assertEqual(line.location_dest_id, self.dest_location)
        self.assertTrue(line.xt_barcode_destination_scanned)
        self.assertEqual(self.picking.xt_barcode_mode, "product")

    def test_scan_package_assigns_current_line_and_blocks_validation_until_packed(self):
        self.picking.picking_type_id.xt_barcode_restrict_put_in_pack = "mandatory"
        self.picking.picking_type_id.xt_barcode_validation_full = False
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        self.picking.action_scan_barcode("BC-PROD-01")
        line = self.picking.xt_barcode_current_line_id
        self.assertEqual(self.picking.xt_barcode_mode, "package")
        self.assertFalse(line.xt_barcode_package_scanned)

        with self.assertRaises(UserError):
            self.picking.action_xt_barcode_validate()

        self.picking.action_scan_barcode("PACK-BOX-01")
        self.assertEqual(line.result_package_id.name, "PACK-BOX-01")
        self.assertTrue(line.xt_barcode_package_scanned)
        self.assertEqual(self.picking.xt_barcode_current_package_id, line.result_package_id)
        self.assertFalse(self.picking._get_barcode_validation_errors())

    def test_main_menu_scan_existing_picking_returns_form_action(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu(self.picking.name)

        self.assertEqual(result["action"]["res_model"], "stock.picking")
        self.assertEqual(result["action"]["res_id"], self.picking.id)

    def test_main_menu_scan_operation_type_creates_new_picking(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("BC-TYPE-INT-01")
        new_picking = self.env["stock.picking"].browse(result["action"]["res_id"])

        self.assertTrue(new_picking.exists())
        self.assertEqual(new_picking.picking_type_id, self.warehouse.int_type_id)
        self.assertEqual(result["action"]["res_model"], "stock.picking")

    def test_main_menu_scan_location_creates_internal_picking(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("BC-SHELF-01")
        new_picking = self.env["stock.picking"].browse(result["action"]["res_id"])

        self.assertTrue(new_picking.exists())
        self.assertEqual(new_picking.picking_type_code, "internal")
        self.assertEqual(new_picking.location_id, self.dest_location)

    def test_main_menu_scan_product_opens_quants(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("BC-PROD-01")

        self.assertEqual(result["action"]["res_model"], "stock.quant")
        self.assertIn(("product_id", "=", self.product.id), result["action"]["domain"])

    def test_main_menu_accepts_lowercase_location_barcode(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("bc-shelf-01")
        new_picking = self.env["stock.picking"].browse(result["action"]["res_id"])

        self.assertTrue(new_picking.exists())
        self.assertEqual(new_picking.picking_type_code, "internal")
        self.assertEqual(new_picking.location_id, self.dest_location)

    def test_main_menu_accepts_normalized_location_barcode_without_separators(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("bc/shelf 01")
        new_picking = self.env["stock.picking"].browse(result["action"]["res_id"])

        self.assertTrue(new_picking.exists())
        self.assertEqual(new_picking.picking_type_code, "internal")
        self.assertEqual(new_picking.location_id, self.dest_location)

    def test_main_menu_scan_lot_and_package_opens_forms(self):
        lot_result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("LOT-EXIST-01")
        package_result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu("PACK-MENU-01")

        self.assertEqual(lot_result["action"]["res_model"], "stock.lot")
        self.assertEqual(lot_result["action"]["res_id"], self.existing_lot.id)
        self.assertEqual(package_result["action"]["res_model"], "stock.package")
        self.assertEqual(package_result["action"]["res_id"], self.package.id)

    def test_root_menu_is_available_from_home(self):
        menu = self.env.ref("xtendoo_stock_barcode.menu_xtendoo_stock_barcode_root")
        action = self.env.ref("xtendoo_stock_barcode.action_xtendoo_stock_barcode_main_menu")

        self.assertEqual(menu.name, "Xtendoo Barcode")
        self.assertFalse(menu.parent_id)
        self.assertEqual(menu.action.id, action.id)


