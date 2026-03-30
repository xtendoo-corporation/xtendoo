# -*- coding: utf-8 -*-
"""Tests unitarios para cash_drawer_utils (sin dependencias de Odoo)."""
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from odoo.addons.xtendoo_open_cash_drawer.models import cash_drawer_utils as utils


class TestParseCommandBytes(unittest.TestCase):
    """Tests para parse_command_bytes()."""

    def test_default_when_empty(self):
        result = utils.parse_command_bytes("")
        self.assertEqual(result, utils.CASH_DRAWER_COMMAND)

    def test_default_when_none(self):
        result = utils.parse_command_bytes(None)
        self.assertEqual(result, utils.CASH_DRAWER_COMMAND)

    def test_standard_escpos(self):
        result = utils.parse_command_bytes("27 112 0 25 250")
        self.assertEqual(result, bytes([27, 112, 0, 25, 250]))

    def test_legacy_esc_i(self):
        result = utils.parse_command_bytes("27 105")
        self.assertEqual(result, bytes([27, 105]))

    def test_star_bel(self):
        result = utils.parse_command_bytes("7")
        self.assertEqual(result, bytes([7]))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            utils.parse_command_bytes("27 abc 0")

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            utils.parse_command_bytes("27 999")


class TestTCPRe(unittest.TestCase):
    """Tests para la expresión regular TCP_RE."""

    def test_valid_ip_port(self):
        m = utils.TCP_RE.match("192.168.1.50:9100")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "192.168.1.50")
        self.assertEqual(m.group(2), "9100")

    def test_valid_hostname_port(self):
        m = utils.TCP_RE.match("printer.local:9100")
        self.assertIsNotNone(m)

    def test_no_port(self):
        self.assertIsNone(utils.TCP_RE.match("/dev/usb/lp0"))

    def test_device_path(self):
        self.assertIsNone(utils.TCP_RE.match("EPSON_TM_T20"))


class TestOpenCashDrawerTCP(unittest.TestCase):
    """Tests para open_cash_drawer() con conexión TCP."""

    def test_tcp_success(self):
        """Verifica que se abre el cajón vía TCP cuando el socket funciona."""
        mock_socket = MagicMock()
        mock_socket.__enter__ = lambda s: s
        mock_socket.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_socket):
            result = utils.open_cash_drawer("192.168.1.50:9100", "27 112 0 25 250")

        self.assertTrue(result)
        mock_socket.sendall.assert_called_once_with(bytes([27, 112, 0, 25, 250]))

    def test_tcp_failure_raises(self):
        """Verifica que se lanza RuntimeError cuando TCP falla y no hay más alternativas."""
        with patch(
            "socket.create_connection",
            side_effect=OSError("Connection refused")
        ):
            with self.assertRaises(RuntimeError) as ctx:
                utils.open_cash_drawer("192.168.1.50:9100")

        self.assertIn("Connection refused", str(ctx.exception))

    def test_uses_default_command_when_none(self):
        """Verifica que se usa el comando por defecto cuando command_bytes_str es None."""
        mock_socket = MagicMock()
        mock_socket.__enter__ = lambda s: s
        mock_socket.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_socket):
            utils.open_cash_drawer("10.0.0.1:9100", None)

        mock_socket.sendall.assert_called_once_with(utils.CASH_DRAWER_COMMAND)


class TestOpenCashDrawerDevice(unittest.TestCase):
    """Tests para open_cash_drawer() con dispositivo local."""

    def test_device_write_success(self):
        """Verifica escritura directa en dispositivo."""
        import io

        fake_device = io.BytesIO()

        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=False), \
             patch("builtins.open", return_value=fake_device), \
             patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = utils.open_cash_drawer("/dev/usb/lp0", "27 105")

        self.assertTrue(result)

    def test_device_not_exists_raises(self):
        """Verifica que se lanza error cuando el dispositivo no existe."""
        with patch("os.path.exists", return_value=False), \
             patch("subprocess.run", return_value=MagicMock(returncode=1)):
            with self.assertRaises(RuntimeError):
                utils.open_cash_drawer("/dev/usb/lp0")


class TestGetDockerGateway(unittest.TestCase):
    """Tests para get_docker_gateway()."""

    def test_parses_gateway(self):
        mock_result = MagicMock()
        mock_result.stdout = "default via 172.17.0.1 dev eth0\n"
        with patch("subprocess.run", return_value=mock_result):
            gw = utils.get_docker_gateway()
        self.assertEqual(gw, "172.17.0.1")

    def test_returns_none_on_error(self):
        with patch("subprocess.run", side_effect=Exception("no ip")):
            gw = utils.get_docker_gateway()
        self.assertIsNone(gw)

    def test_returns_none_when_no_via(self):
        mock_result = MagicMock()
        mock_result.stdout = "unreachable default\n"
        with patch("subprocess.run", return_value=mock_result):
            gw = utils.get_docker_gateway()
        self.assertIsNone(gw)


class TestResolvePrinterAddress(unittest.TestCase):
    """Tests para resolve_printer_address() — soporte Docker 'host:PORT'."""

    def test_passthrough_ip_port(self):
        """Addresses with an explicit IP are returned unchanged."""
        addr = utils.resolve_printer_address("192.168.1.50:9100")
        self.assertEqual(addr, "192.168.1.50:9100")

    def test_passthrough_device_path(self):
        """Device paths (/dev/...) are returned unchanged."""
        addr = utils.resolve_printer_address("/dev/usb/lp0")
        self.assertEqual(addr, "/dev/usb/lp0")

    def test_passthrough_cups_name(self):
        """CUPS printer names (no port) are returned unchanged."""
        addr = utils.resolve_printer_address("EPSON_TM_T20")
        self.assertEqual(addr, "EPSON_TM_T20")

    def test_host_keyword_resolves_to_gateway(self):
        """'host:PORT' is replaced by '<docker-gateway>:PORT'."""
        mock_result = MagicMock()
        mock_result.stdout = "default via 172.17.0.1 dev eth0\n"
        with patch("subprocess.run", return_value=mock_result):
            addr = utils.resolve_printer_address("host:9100")
        self.assertEqual(addr, "172.17.0.1:9100")

    def test_host_keyword_case_insensitive(self):
        """'HOST:PORT' (uppercase) is also resolved."""
        mock_result = MagicMock()
        mock_result.stdout = "default via 172.17.0.1 dev eth0\n"
        with patch("subprocess.run", return_value=mock_result):
            addr = utils.resolve_printer_address("HOST:9100")
        self.assertEqual(addr, "172.17.0.1:9100")

    def test_host_keyword_no_gateway_raises(self):
        """RuntimeError raised when 'host' is used but no gateway is found."""
        with patch("subprocess.run", side_effect=Exception("no ip route")):
            with self.assertRaises(RuntimeError) as ctx:
                utils.resolve_printer_address("host:9100")
        self.assertIn("Docker gateway not detected", str(ctx.exception))

