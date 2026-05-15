from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestSaleBarcodeScanner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Scanner Customer"})
        cls.scanned_product = cls.env["product.product"].create(
            {
                "name": "Scanner Product",
                "barcode": "SCAN-001",
                "sale_ok": True,
            }
        )
        cls.duplicate_product = cls.env["product.product"].create(
            {
                "name": "Scanner Product Duplicate",
                "barcode": "SCAN-DUPLICATE-1",
                "sale_ok": True,
            }
        )
        cls.ambiguous_product = cls.env["product.product"].create(
            {
                "name": "Scanner Product Ambiguous",
                "barcode": "SCAN-DUPLICATE-2",
                "sale_ok": True,
            }
        )
        cls.alt_uom = cls.env["uom.uom"].create(
            {
                "name": "Caja x2",
                "relative_uom_id": cls.scanned_product.uom_id.id,
                "relative_factor": 2.0,
            }
        )
        cls.not_sale_product = cls.env["product.product"].create(
            {
                "name": "Scanner Hidden Product",
                "barcode": "SCAN-HIDDEN",
                "sale_ok": False,
            }
        )

    def _new_order(self, **extra_vals):
        vals = {
            "partner_id": self.partner.id,
            "pricelist_id": self.partner.property_product_pricelist.id,
            "currency_id": self.partner.property_product_pricelist.currency_id.id,
            **extra_vals,
        }
        return self.env["sale.order"].new(vals)

    def test_helper_methods_return_expected_values(self):
        order = self._new_order(name=False)

        self.assertEqual(order._barcode_scan_allowed_states(), {"draft", "sent"})
        self.assertTrue(order._is_barcode_scan_allowed())
        self.assertEqual(
            order._get_barcode_scan_product_domain("SCAN-001"),
            [("barcode", "=", "SCAN-001"), ("sale_ok", "=", True)],
        )
        self.assertEqual(
            order._prepare_scanned_order_line_values(self.scanned_product)["product_id"],
            self.scanned_product.id,
        )
        self.assertEqual(
            order._barcode_scan_log_prefix(),
            "[sale_barcode_scanner] [sale.order(new)]",
        )

    def test_find_barcode_scan_products_only_returns_saleable_products(self):
        order = self._new_order()

        self.assertEqual(order._find_barcode_scan_products("SCAN-001"), self.scanned_product)
        self.assertFalse(order._find_barcode_scan_products(self.not_sale_product.barcode))

    def test_get_existing_scanned_product_line_ignores_display_lines(self):
        order = self._new_order(
            order_line=[
                Command.create({"display_type": "line_section", "name": "Section"}),
                Command.create(
                    {
                        "product_id": self.scanned_product.id,
                        "product_uom_qty": 1.0,
                        "sequence": 20,
                    }
                ),
            ]
        )

        line = order._get_existing_scanned_product_line(self.scanned_product)

        self.assertEqual(line.product_id, self.scanned_product)
        self.assertFalse(line.display_type)

    def test_scan_ignores_empty_or_whitespace_barcodes(self):
        order = self._new_order()

        self.assertFalse(order.on_barcode_scanned(""))
        self.assertFalse(order.on_barcode_scanned("   "))
        self.assertEqual(order.action_scan_barcode("   ")["status"], "ignored")
        self.assertFalse(order.order_line)

    def test_scan_creates_line_on_unsaved_order(self):
        order = self._new_order()

        result = order.on_barcode_scanned("SCAN-001")

        self.assertFalse(result)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.scanned_product)
        self.assertEqual(order.order_line.product_uom_qty, 1.0)

    def test_scan_increments_existing_line_on_unsaved_order(self):
        order = self._new_order(
            order_line=[Command.create({"product_id": self.scanned_product.id, "product_uom_qty": 1.0})]
        )

        result = order.on_barcode_scanned("SCAN-001")

        self.assertFalse(result)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_uom_qty, 2.0)

    def test_scan_increments_first_matching_line(self):
        order = self._new_order(
            order_line=[
                Command.create({
                    "product_id": self.scanned_product.id,
                    "product_uom_qty": 1.0,
                    "sequence": 5,
                }),
                Command.create({
                    "product_id": self.scanned_product.id,
                    "product_uom_qty": 4.0,
                    "sequence": 15,
                }),
            ]
        )

        result = order.on_barcode_scanned("SCAN-001")

        self.assertFalse(result)
        self.assertEqual(order.order_line[0].product_uom_qty, 2.0)
        self.assertEqual(order.order_line[1].product_uom_qty, 4.0)

    def test_scan_warns_when_barcode_not_found(self):
        order = self._new_order()

        result = order.on_barcode_scanned("UNKNOWN")

        self.assertEqual(result["warning"]["title"], "Escaneo de código de barras")
        self.assertIn("No se ha encontrado ningún producto vendible", result["warning"]["message"])
        self.assertFalse(order.order_line)

    def test_scan_warns_when_barcode_is_ambiguous(self):
        order = self._new_order()

        with patch.object(
            type(order),
            "_find_barcode_scan_products",
            autospec=True,
            return_value=self.duplicate_product | self.ambiguous_product,
        ):
            result = order.on_barcode_scanned("SCAN-DUPLICATE")

        self.assertEqual(result["warning"]["title"], "Escaneo de código de barras")
        self.assertIn("varios productos vendibles", result["warning"]["message"])
        self.assertFalse(order.order_line)

    def test_scan_warns_when_existing_line_has_different_uom(self):
        order = self._new_order(
            order_line=[
                Command.create(
                    {
                        "product_id": self.scanned_product.id,
                        "product_uom_id": self.alt_uom.id,
                        "product_uom_qty": 1.0,
                    }
                )
            ]
        )

        result = order.on_barcode_scanned("SCAN-001")

        self.assertEqual(result["warning"]["title"], "Escaneo de código de barras")
        self.assertIn("unidad de medida distinta", result["warning"]["message"])
        self.assertEqual(order.order_line.product_uom_qty, 1.0)

    def test_scan_warns_when_order_is_not_editable(self):
        order = self._new_order(state="sale")

        result = order.on_barcode_scanned("SCAN-001")

        self.assertEqual(result["warning"]["title"], "Escaneo de código de barras")
        self.assertIn("El pedido no es editable", result["warning"]["message"])
        self.assertFalse(order.order_line)

    def test_action_scan_barcode_raises_when_order_is_not_editable(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.state = "sale"

        with self.assertRaises(UserError):
            order.action_scan_barcode("SCAN-001")

    def test_action_scan_barcode_creates_and_increments_on_saved_order(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})

        create_result = order.action_scan_barcode("SCAN-001")
        increment_result = order.action_scan_barcode("SCAN-001")

        self.assertEqual(create_result["status"], "created")
        self.assertEqual(increment_result["status"], "incremented")
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.scanned_product)
        self.assertEqual(order.order_line.product_uom_qty, 2.0)

    def test_action_scan_barcode_raises_on_error(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})

        with self.assertRaises(UserError):
            order.action_scan_barcode("UNKNOWN")

