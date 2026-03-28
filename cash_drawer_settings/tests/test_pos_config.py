# -*- coding: utf-8 -*-
"""Tests de integración para pos.config (action_pos_open_cash_drawer)."""
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosConfigCashDrawer(TransactionCase):
    """Tests para la extensión de pos.config."""

    def setUp(self):
        super().setUp()
        # Buscar una configuración de TPV existente o crear una de prueba
        self.pos_config = self.env.ref(
            "point_of_sale.pos_config_main", raise_if_not_found=False
        ) or self.env["pos.config"].search([], limit=1)

        if not self.pos_config:
            # Crear una configuración mínima para los tests
            self.pos_config = self.env["pos.config"].create({
                "name": "Test POS Cash Drawer",
            })
            self._created_pos_config = True
        else:
            self._created_pos_config = False

    def tearDown(self):
        if getattr(self, "_created_pos_config", False):
            self.pos_config.unlink()
        super().tearDown()

    # ------------------------------------------------------------------
    # Tests del campo
    # ------------------------------------------------------------------

    def test_field_exists(self):
        """Verifica que el campo cash_drawer_pos_enabled existe en pos.config."""
        self.assertIn(
            "cash_drawer_pos_enabled",
            self.pos_config._fields,
            "El campo cash_drawer_pos_enabled debe existir en pos.config",
        )

    def test_field_default_false(self):
        """Verifica que el campo está desactivado por defecto."""
        config = self.env["pos.config"].create({"name": "Test Cash Drawer Config"})
        self.assertFalse(config.cash_drawer_pos_enabled)
        config.unlink()

    def test_field_can_be_enabled(self):
        """Verifica que el campo se puede activar."""
        config = self.env["pos.config"].create({
            "name": "Test Cash Drawer Enabled",
            "cash_drawer_pos_enabled": True,
        })
        self.assertTrue(config.cash_drawer_pos_enabled)
        config.unlink()

    # ------------------------------------------------------------------
    # Tests del método RPC
    # ------------------------------------------------------------------

    def test_rpc_raises_without_printer(self):
        """Verifica que action_pos_open_cash_drawer lanza UserError sin impresora."""
        # Asegurar que no hay impresora configurada
        self.env["ir.config_parameter"].sudo().set_param(
            "cash_drawer_settings.printer_path", ""
        )
        with self.assertRaises(UserError) as ctx:
            self.pos_config.action_pos_open_cash_drawer()
        self.assertIn("No hay ninguna impresora", str(ctx.exception))

    def test_rpc_calls_open_cash_drawer(self):
        """Verifica que se llama a open_cash_drawer con los parámetros correctos."""
        self.env["ir.config_parameter"].sudo().set_param(
            "cash_drawer_settings.printer_path", "192.168.1.50:9100"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "cash_drawer_settings.command_bytes", "27 112 0 25 250"
        )

        with patch(
            "odoo.addons.cash_drawer_settings.models.cash_drawer_utils.open_cash_drawer",
            return_value=True,
        ) as mock_open:
            result = self.pos_config.action_pos_open_cash_drawer()

        mock_open.assert_called_once_with(
            "192.168.1.50:9100", "27 112 0 25 250"
        )
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")

    def test_rpc_raises_on_connection_error(self):
        """Verifica que RuntimeError se convierte en UserError."""
        self.env["ir.config_parameter"].sudo().set_param(
            "cash_drawer_settings.printer_path", "192.168.1.50:9100"
        )
        with patch(
            "odoo.addons.cash_drawer_settings.models.cash_drawer_utils.open_cash_drawer",
            side_effect=RuntimeError("Connection refused"),
        ):
            with self.assertRaises(UserError) as ctx:
                self.pos_config.action_pos_open_cash_drawer()
        self.assertIn("Connection refused", str(ctx.exception))

    def test_rpc_uses_default_command(self):
        """Verifica que se usa el comando por defecto cuando command_bytes está vacío."""
        self.env["ir.config_parameter"].sudo().set_param(
            "cash_drawer_settings.printer_path", "192.168.1.50:9100"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "cash_drawer_settings.command_bytes", ""
        )

        with patch(
            "odoo.addons.cash_drawer_settings.models.cash_drawer_utils.open_cash_drawer",
            return_value=True,
        ) as mock_open:
            self.pos_config.action_pos_open_cash_drawer()

        mock_open.assert_called_once_with("192.168.1.50:9100", "")

