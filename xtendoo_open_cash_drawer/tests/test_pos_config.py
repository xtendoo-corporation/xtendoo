# -*- coding: utf-8 -*-
"""Tests for pos.config dummy print fields and direct ESC/POS method."""
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosConfigCashDrawer(TransactionCase):
    """Tests for the cash drawer extension of pos.config."""

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create({
            "name": "Test POS Cash Drawer",
        })

    # ------------------------------------------------------------------
    # Field existence & defaults
    # ------------------------------------------------------------------

    def test_fields_exist(self):
        """Verify that all new fields exist in pos.config."""
        fields_to_check = [
            "cash_drawer_printer_address",
            "cash_drawer_command_bytes",
            "cash_drawer_dummy_print",
            "cash_drawer_dummy_text",
            "cash_drawer_web_print_fallback",
        ]
        for field in fields_to_check:
            self.assertIn(
                field,
                self.pos_config._fields,
                "The field %s must exist in pos.config" % field,
            )

    def test_fields_defaults(self):
        """Verify default values for the new fields."""
        self.assertFalse(self.pos_config.cash_drawer_printer_address)
        self.assertEqual(self.pos_config.cash_drawer_command_bytes, "27 112 0 25 250")
        self.assertFalse(self.pos_config.cash_drawer_dummy_print)
        self.assertEqual(self.pos_config.cash_drawer_dummy_text, ".")
        self.assertFalse(self.pos_config.cash_drawer_web_print_fallback)

    def test_fields_can_be_set(self):
        """Verify the fields can be modified."""
        self.pos_config.write({
            "cash_drawer_printer_address": "192.168.1.50:9100",
            "cash_drawer_command_bytes": "27 112 1 25 250",
            "cash_drawer_dummy_print": True,
            "cash_drawer_dummy_text": "OPEN",
            "cash_drawer_web_print_fallback": True,
        })
        self.assertEqual(self.pos_config.cash_drawer_printer_address, "192.168.1.50:9100")
        self.assertEqual(self.pos_config.cash_drawer_command_bytes, "27 112 1 25 250")
        self.assertTrue(self.pos_config.cash_drawer_dummy_print)
        self.assertEqual(self.pos_config.cash_drawer_dummy_text, "OPEN")
        self.assertTrue(self.pos_config.cash_drawer_web_print_fallback)

    # ------------------------------------------------------------------
    # open_cash_drawer_direct()
    # ------------------------------------------------------------------

    def test_open_cash_drawer_direct_no_address_raises(self):
        """UserError raised when no printer address is configured."""
        with self.assertRaises(UserError):
            self.pos_config.open_cash_drawer_direct()

    def test_open_cash_drawer_direct_success(self):
        """Returns {'success': True} when the utility succeeds."""
        self.pos_config.cash_drawer_printer_address = "192.168.1.50:9100"
        module = "odoo.addons.xtendoo_open_cash_drawer.models.pos_config"
        with patch("%s.open_cash_drawer" % module, return_value=True) as mock_fn:
            result = self.pos_config.open_cash_drawer_direct()
        self.assertEqual(result, {"success": True})
        mock_fn.assert_called_once_with("192.168.1.50:9100", "27 112 0 25 250")

    def test_open_cash_drawer_direct_runtime_error_raises_user_error(self):
        """RuntimeError from the utility is wrapped in UserError."""
        self.pos_config.cash_drawer_printer_address = "192.168.1.50:9100"
        module = "odoo.addons.xtendoo_open_cash_drawer.models.pos_config"
        with patch(
            "%s.open_cash_drawer" % module,
            side_effect=RuntimeError("Connection refused"),
        ):
            with self.assertRaises(UserError) as ctx:
                self.pos_config.open_cash_drawer_direct()
        self.assertIn("Connection refused", str(ctx.exception))

    def test_open_cash_drawer_direct_uses_custom_command(self):
        """Custom command bytes are forwarded to the utility."""
        self.pos_config.cash_drawer_printer_address = "/dev/usb/lp0"
        self.pos_config.cash_drawer_command_bytes = "7"
        module = "odoo.addons.xtendoo_open_cash_drawer.models.pos_config"
        with patch("%s.open_cash_drawer" % module, return_value=True) as mock_fn:
            self.pos_config.open_cash_drawer_direct()
        mock_fn.assert_called_once_with("/dev/usb/lp0", "7")

    def test_open_cash_drawer_direct_empty_command_passes_none(self):
        """Empty command bytes string is normalised to None (uses default)."""
        self.pos_config.cash_drawer_printer_address = "10.0.0.1:9100"
        self.pos_config.cash_drawer_command_bytes = ""
        module = "odoo.addons.xtendoo_open_cash_drawer.models.pos_config"
        with patch("%s.open_cash_drawer" % module, return_value=True) as mock_fn:
            self.pos_config.open_cash_drawer_direct()
        mock_fn.assert_called_once_with("10.0.0.1:9100", None)

