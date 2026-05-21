from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from lxml import etree


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
        cls.product_secondary = cls.env["product.product"].create(
            {
                "name": "Barcode Product Secondary",
                "barcode": "BC-PROD-02",
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
        cls.pda_view = cls.env.ref(
            "xtendoo_stock_barcode.view_picking_form_xtendoo_stock_barcode_pda_intuitive"
        )

    def setUp(self):
        super().setUp()
        self.picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.int_type_id.id,
                "location_id": self.source_location.id,
                "location_dest_id": self.source_location.id,
            }
        )

    def test_action_open_pda_uses_custom_xtendoo_view(self):
        action = self.picking.action_xt_barcode_open_pda()

        self.assertEqual(action["res_model"], "stock.picking")
        self.assertEqual(action["res_id"], self.picking.id)
        self.assertEqual(action["views"][0][0], self.pda_view.id)

    def standard_form_view_exposes_pda_access_and_barcode_handler(self):
        view = self.env["stock.picking"].get_view(
            view_id=self.env.ref("stock.view_picking_form").id,
            view_type="form",
        )
        arch = etree.fromstring(view["arch"].encode())

        pda_button = arch.xpath("//button[@name='action_xt_barcode_open_pda']")
        barcode_handler = arch.xpath(
            "//field[@name='_barcode_scanned'][@widget='barcode_handler']"
        )

        self.assertEqual(len(pda_button), 1)
        self.assertEqual(pda_button[0].attrib.get("string"), "Comprobación PDA")
        self.assertEqual(len(barcode_handler), 1)
        self.assertEqual(barcode_handler[0].attrib.get("class"), "d-none")

    test_standard_form_view_exposes_pda_access_and_barcode_handler = (
        standard_form_view_exposes_pda_access_and_barcode_handler
    )

    def pda_form_view_guides_the_first_scan_and_omits_manual_controls(self):
        view = self.env["stock.picking"].get_view(
            view_id=self.pda_view.id,
            view_type="form",
        )
        arch = etree.fromstring(view["arch"].encode())

        scanner_fields = arch.xpath(
            "//field[@name='_barcode_scanned'][@widget='xtendoo_stock_barcode_scanner']"
        )
        zero_scan_alerts = arch.xpath(
            "//div[contains(@class, 'alert')][.//field[@name='xt_barcode_zero_scan_message']]"
        )
        focus_labels = arch.xpath("//field[@name='xt_barcode_focus_product_label']")
        next_steps = arch.xpath("//field[@name='xt_barcode_next_step']")
        pending_summaries = arch.xpath("//field[@name='xt_barcode_pending_summary']")
        removed_controls = arch.xpath(
            "//button[@name='action_xt_barcode_set_mode_product' or @name='action_xt_barcode_set_mode_source' or @name='action_xt_barcode_set_mode_destination' or @name='action_xt_barcode_set_mode_lot' or @name='action_xt_barcode_set_mode_package' or @name='action_xt_barcode_reset_context']"
        )

        self.assertEqual(len(scanner_fields), 1)
        self.assertEqual(len(zero_scan_alerts), 1)
        self.assertIn("xt_barcode_has_scanned_products", zero_scan_alerts[0].attrib["invisible"])
        self.assertIn("xt_barcode_zero_scan_message", zero_scan_alerts[0].attrib["invisible"])
        self.assertEqual(len(focus_labels), 1)
        self.assertGreaterEqual(len(next_steps), 2)
        self.assertEqual(len(pending_summaries), 1)
        self.assertFalse(removed_controls)

    test_pda_form_view_guides_the_first_scan_and_omits_manual_controls = (
        pda_form_view_guides_the_first_scan_and_omits_manual_controls
    )

    def opening_pda_falls_back_to_the_standard_form_when_scanning_is_not_allowed(self):
        self.picking.action_cancel()

        action = self.picking.action_xt_barcode_open_pda()

        self.assertEqual(action["res_model"], "stock.picking")
        self.assertEqual(action["res_id"], self.picking.id)
        self.assertEqual(action["views"][0][0], self.env.ref("stock.view_picking_form").id)
        self.assertEqual(action["target"], "current")
        self.assertEqual(action["context"]["active_id"], self.picking.id)
        self.assertEqual(action["context"]["active_ids"], [self.picking.id])

    test_opening_pda_falls_back_to_the_standard_form_when_scanning_is_not_allowed = (
        opening_pda_falls_back_to_the_standard_form_when_scanning_is_not_allowed
    )

    def test_scan_source_location_sets_context(self):
        self.picking.xt_barcode_mode = "source"
        self.picking.action_scan_barcode("BC-SHELF-01")
        self.assertEqual(self.picking.xt_barcode_source_location_id, self.dest_location)
        self.assertEqual(self.picking.xt_barcode_mode, "product")

    def test_scan_source_location_accepts_lowercase_barcode(self):
        self.picking.xt_barcode_mode = "source"
        self.picking.action_scan_barcode("bc-shelf-01")
        self.assertEqual(self.picking.xt_barcode_source_location_id, self.dest_location)

    def test_scan_source_location_accepts_normalized_barcode_without_separators(self):
        self.picking.xt_barcode_mode = "source"
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

    def test_pda_comparison_tracks_pending_partial_and_complete(self):
        move = self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 3.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        move.invalidate_recordset(["xt_barcode_remaining_qty", "xt_barcode_check_state"])
        self.picking.invalidate_recordset([
            "xt_barcode_expected_move_count",
            "xt_barcode_pending_move_count",
            "xt_barcode_compare_state",
        ])
        self.assertEqual(move.xt_barcode_check_state, "pending")
        self.assertEqual(move.xt_barcode_remaining_qty, 3.0)
        self.assertEqual(self.picking.xt_barcode_compare_state, "pending")

        self.picking.action_scan_barcode("BC-PROD-01")
        self.picking.action_scan_barcode("BC-PROD-01")
        move.invalidate_recordset(["quantity", "xt_barcode_remaining_qty", "xt_barcode_check_state"])
        self.picking.invalidate_recordset([
            "xt_barcode_checked_move_count",
            "xt_barcode_pending_move_count",
            "xt_barcode_compare_state",
        ])
        self.assertEqual(move.quantity, 2.0)
        self.assertEqual(move.xt_barcode_remaining_qty, 1.0)
        self.assertEqual(move.xt_barcode_check_state, "partial")
        self.assertEqual(self.picking.xt_barcode_compare_state, "partial")

        self.picking.action_scan_barcode("BC-PROD-01")
        move.invalidate_recordset(["quantity", "xt_barcode_remaining_qty", "xt_barcode_check_state"])
        self.picking.invalidate_recordset([
            "xt_barcode_checked_move_count",
            "xt_barcode_pending_move_count",
            "xt_barcode_compare_state",
        ])
        self.assertEqual(move.quantity, 3.0)
        self.assertEqual(move.xt_barcode_remaining_qty, 0.0)
        self.assertEqual(move.xt_barcode_check_state, "complete")
        self.assertEqual(self.picking.xt_barcode_checked_move_count, 1)
        self.assertEqual(self.picking.xt_barcode_pending_move_count, 0)
        self.assertEqual(self.picking.xt_barcode_compare_state, "complete")

    def test_pda_shows_zero_scan_state_until_first_product_scan(self):
        self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 2.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        self.picking.invalidate_recordset([
            "xt_barcode_has_scanned_products",
            "xt_barcode_zero_scan_message",
            "xt_barcode_next_step",
            "xt_barcode_focus_product_label",
            "xt_barcode_focus_quantity_label",
            "xt_barcode_compare_state",
        ])

        self.assertFalse(self.picking.xt_barcode_has_scanned_products)
        self.assertEqual(
            self.picking.xt_barcode_zero_scan_message,
            "Aún no se ha escaneado ningún producto.",
        )
        self.assertEqual(self.picking.xt_barcode_compare_state, "pending")
        self.assertEqual(
            self.picking.xt_barcode_focus_product_label,
            f"Primer producto: {self.product.display_name}",
        )
        self.assertIn("Escanea", self.picking.xt_barcode_next_step)

        self.picking.action_scan_barcode("BC-PROD-01")
        self.picking.invalidate_recordset([
            "xt_barcode_has_scanned_products",
            "xt_barcode_zero_scan_message",
            "xt_barcode_focus_product_label",
        ])

        self.assertTrue(self.picking.xt_barcode_has_scanned_products)
        self.assertFalse(self.picking.xt_barcode_zero_scan_message)
        self.assertEqual(self.picking.xt_barcode_focus_product_label, self.product.display_name)

    def test_on_barcode_scanned_uses_persisted_picking_from_form_onchange(self):
        self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        pseudo_picking = self.picking.with_context(active_id=self.picking.id).new({})

        result = pseudo_picking.on_barcode_scanned("BC-PROD-01")

        self.assertFalse(result)
        self.assertTrue(self.picking.xt_barcode_current_line_id)
        self.assertEqual(self.picking.xt_barcode_current_line_id.product_id, self.product)
        self.assertEqual(self.picking.xt_barcode_current_line_id.quantity, 1.0)
        self.assertTrue(self.picking.xt_barcode_has_scanned_products)
        self.assertFalse(self.picking.xt_barcode_zero_scan_message)
        self.assertTrue(pseudo_picking.xt_barcode_has_scanned_products)
        self.assertEqual(pseudo_picking.xt_barcode_current_line_id, self.picking.xt_barcode_current_line_id)
        self.assertEqual(pseudo_picking.xt_barcode_compare_state, "complete")
        self.assertFalse(pseudo_picking.xt_barcode_zero_scan_message)

    def test_pda_focus_prioritizes_partial_product_before_other_pending_lines(self):
        first_move = self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 3.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        second_move = self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product_secondary.id,
                "product_uom": self.product_secondary.uom_id.id,
                "product_uom_qty": 1.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.picking.xt_barcode_source_location_id = self.source_location
        self.picking.xt_barcode_destination_location_id = self.dest_location

        self.picking.action_scan_barcode("BC-PROD-01")

        self.picking.invalidate_recordset([
            "xt_barcode_pending_move_ids",
            "xt_barcode_focus_move_id",
            "xt_barcode_focus_product_label",
            "xt_barcode_focus_quantity_label",
        ])
        first_move.invalidate_recordset(["xt_barcode_check_state", "xt_barcode_remaining_qty"])
        second_move.invalidate_recordset(["xt_barcode_check_state", "xt_barcode_remaining_qty"])

        self.assertEqual(first_move.xt_barcode_check_state, "partial")
        self.assertEqual(second_move.xt_barcode_check_state, "pending")
        self.assertEqual(self.picking.xt_barcode_pending_move_ids[:2], first_move | second_move)
        self.assertEqual(self.picking.xt_barcode_focus_move_id, first_move)
        self.assertEqual(self.picking.xt_barcode_focus_product_label, self.product.display_name)
        self.assertIn("Faltan 2.0", self.picking.xt_barcode_focus_quantity_label)

    def test_pda_uses_scanned_move_lines_not_move_quantity_for_completion(self):
        move = self.env["stock.move"].create(
            {
                "picking_id": self.picking.id,
                "picking_type_id": self.picking.picking_type_id.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 2.0,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "picking_id": self.picking.id,
                "move_id": move.id,
                "company_id": self.picking.company_id.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "location_id": self.source_location.id,
                "location_dest_id": self.dest_location.id,
                "quantity": 2.0,
                "picked": False,
                "xt_barcode_product_scanned": False,
            }
        )

        move.invalidate_recordset([
            "xt_barcode_scanned_qty",
            "xt_barcode_remaining_qty",
            "xt_barcode_check_state",
        ])
        self.picking.invalidate_recordset([
            "xt_barcode_checked_move_count",
            "xt_barcode_pending_move_count",
            "xt_barcode_compare_state",
        ])

        self.assertEqual(move.xt_barcode_scanned_qty, 0.0)
        self.assertEqual(move.xt_barcode_remaining_qty, 2.0)
        self.assertEqual(move.xt_barcode_check_state, "pending")
        self.assertEqual(self.picking.xt_barcode_checked_move_count, 0)
        self.assertEqual(self.picking.xt_barcode_pending_move_count, 1)
        self.assertEqual(self.picking.xt_barcode_compare_state, "pending")

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

    def test_main_menu_scan_existing_picking_returns_pda_action(self):
        result = self.env["stock.picking"].action_xt_barcode_scan_from_main_menu(self.picking.name)

        self.assertEqual(result["action"]["res_model"], "stock.picking")
        self.assertEqual(result["action"]["res_id"], self.picking.id)
        self.assertEqual(result["action"]["views"][0][0], self.pda_view.id)

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
        self.assertEqual(result["action"]["views"][0][0], self.pda_view.id)

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
        central_menu = self.env.ref("todopinturas_stock_barcode.menu_todopinturas_stock_barcode_root")

        self.assertEqual(menu.name, "Xtendoo Barcode")
        self.assertFalse(menu.parent_id)
        self.assertEqual(menu.action.id, action.id)
        self.assertEqual(menu.child_id, central_menu)

