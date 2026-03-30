# -*- coding: utf-8 -*-
"""Tests for pos.config dummy print fields."""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosConfigCashDrawer(TransactionCase):
    """Tests for the dummy print extension of pos.config."""

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create({
            "name": "Test POS Cash Drawer",
        })

    def test_fields_exist(self):
        """Verify that the new fields exist in pos.config."""
        fields_to_check = [
            "cash_drawer_dummy_print",
            "cash_drawer_dummy_text",
            "cash_drawer_web_print_fallback",
        ]
        for field in fields_to_check:
            self.assertIn(
                field,
                self.pos_config._fields,
                f"The field {field} must exist in pos.config",
            )

    def test_fields_defaults(self):
        """Verify default values for the new fields."""
        self.assertFalse(self.pos_config.cash_drawer_dummy_print)
        self.assertEqual(self.pos_config.cash_drawer_dummy_text, ".")
        self.assertFalse(self.pos_config.cash_drawer_web_print_fallback)

    def test_fields_can_be_set(self):
        """Verify the fields can be modified."""
        self.pos_config.write({
            "cash_drawer_dummy_print": True,
            "cash_drawer_dummy_text": "OPEN",
            "cash_drawer_web_print_fallback": True,
        })
        self.assertTrue(self.pos_config.cash_drawer_dummy_print)
        self.assertEqual(self.pos_config.cash_drawer_dummy_text, "OPEN")
        self.assertTrue(self.pos_config.cash_drawer_web_print_fallback)
