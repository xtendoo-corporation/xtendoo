# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Tests del módulo xtendoo_cash_drawer.

Arquitectura probada: frontend POS → bridge local (fetch directo desde el navegador).
El backend Python ya no es la vía principal de apertura del cajón.

Cobertura:
- Funciones legacy del controlador (_detect_docker_host_ip, _resolve_url,
  CashDrawerController.open_cash_drawer): mantenidas para no romper tests
  existentes del código legacy que se conserva por compatibilidad.
- pos.config: nuevos campos (cash_drawer_use_bridge, cash_drawer_bridge_url,
  cash_drawer_printer_name, cash_drawer_api_key, cash_drawer_auto_open).
  Campo legacy cash_drawer_open_url.
  action_test_cash_drawer con nueva firma de parámetros.
- pos.config._compute_effective_bridge_url: lógica de fallback.
- res.config.settings: campos relacionados y action_test_cash_drawer.
"""

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.xtendoo_cash_drawer.controllers.cash_drawer import (
    CashDrawerController,
    _detect_docker_host_ip,
    _resolve_url,
)

_CONTROLLER_MODULE = "odoo.addons.xtendoo_cash_drawer.controllers.cash_drawer"


# ---------------------------------------------------------------------------
# _detect_docker_host_ip  (funciones del controlador legacy)
# ---------------------------------------------------------------------------


@tagged("post_install", "-at_install", "xtendoo_cash_drawer")
class TestDetectDockerHostIp(TransactionCase):
    """Pruebas para la función auxiliar _detect_docker_host_ip() del controlador legacy."""

    def test_returns_ip_when_host_docker_internal_resolves(self):
        """Debe retornar la IP cuando host.docker.internal resuelve correctamente."""
        with patch(f"{_CONTROLLER_MODULE}.socket.gethostbyname", return_value="172.17.0.1"):
            ip = _detect_docker_host_ip()
        self.assertEqual(ip, "172.17.0.1")

    def test_reads_gateway_from_proc_net_route_when_hostname_fails(self):
        """Debe leer la IP del gateway desde /proc/net/route si hostname falla."""
        # 0101A8C0 = 192.168.1.1 en hexadecimal little-endian
        route_data = (
            "Iface\tDestination\tGateway\tFlags\n"
            "eth0\t00000000\t0101A8C0\t0003\n"
        )
        with patch(f"{_CONTROLLER_MODULE}.socket.gethostbyname", side_effect=OSError):
            with patch("builtins.open", return_value=StringIO(route_data)):
                ip = _detect_docker_host_ip()
        self.assertEqual(ip, "192.168.1.1")

    def test_skips_non_default_routes_in_proc_net_route(self):
        """Solo debe considerar la ruta por defecto (destino 00000000)."""
        route_data = (
            "Iface\tDestination\tGateway\tFlags\n"
            "eth0\tFE04A8C0\t0101A8C0\t0001\n"
            "eth0\t00000000\t0201A8C0\t0003\n"
        )
        with patch(f"{_CONTROLLER_MODULE}.socket.gethostbyname", side_effect=OSError):
            with patch("builtins.open", return_value=StringIO(route_data)):
                ip = _detect_docker_host_ip()
        # 0201A8C0 → 192.168.1.2
        self.assertEqual(ip, "192.168.1.2")

    def test_returns_none_when_both_methods_fail(self):
        """Debe retornar None cuando ni hostname ni /proc/net/route funcionan."""
        with patch(f"{_CONTROLLER_MODULE}.socket.gethostbyname", side_effect=OSError):
            with patch("builtins.open", side_effect=OSError):
                ip = _detect_docker_host_ip()
        self.assertIsNone(ip)

    def test_returns_none_when_proc_route_has_no_default(self):
        """Debe retornar None cuando /proc/net/route no tiene ruta por defecto."""
        route_data = "Iface\tDestination\tGateway\n"
        with patch(f"{_CONTROLLER_MODULE}.socket.gethostbyname", side_effect=OSError):
            with patch("builtins.open", return_value=StringIO(route_data)):
                ip = _detect_docker_host_ip()
        self.assertIsNone(ip)


# ---------------------------------------------------------------------------
# _resolve_url  (funciones del controlador legacy)
# ---------------------------------------------------------------------------


@tagged("post_install", "-at_install", "xtendoo_cash_drawer")
class TestResolveUrl(TransactionCase):
    """Pruebas para la función auxiliar _resolve_url() del controlador legacy."""

    def test_non_localhost_url_returned_unchanged(self):
        """Una URL sin localhost/127.0.0.1 se devuelve como lista unitaria sin cambios."""
        url = "http://192.168.1.10:3211/open"
        result = _resolve_url(url)
        self.assertEqual(result, [url])

    def test_localhost_url_generates_docker_candidate_first(self):
        """Con localhost, el primer candidato debe usar la IP del host Docker."""
        url = "http://localhost:3211/open"
        with patch(f"{_CONTROLLER_MODULE}._detect_docker_host_ip", return_value="172.17.0.1"):
            result = _resolve_url(url)
        self.assertEqual(result[0], "http://172.17.0.1:3211/open")

    def test_localhost_url_includes_original_as_last_fallback(self):
        """La URL original siempre debe aparecer como último recurso."""
        url = "http://localhost:3211/open"
        with patch(f"{_CONTROLLER_MODULE}._detect_docker_host_ip", return_value="172.17.0.1"):
            result = _resolve_url(url)
        self.assertEqual(result[-1], url)

    def test_127_url_replaces_correctly(self):
        """La sustitución también funciona con 127.0.0.1."""
        url = "http://127.0.0.1:3211/open"
        with patch(f"{_CONTROLLER_MODULE}._detect_docker_host_ip", return_value="10.0.2.2"):
            result = _resolve_url(url)
        self.assertEqual(result[0], "http://10.0.2.2:3211/open")
        self.assertIn(url, result)

    def test_localhost_without_docker_host_returns_only_original(self):
        """Sin IP Docker disponible, solo debe haber la URL original en la lista."""
        url = "http://127.0.0.1:3211/open"
        with patch(f"{_CONTROLLER_MODULE}._detect_docker_host_ip", return_value=None):
            result = _resolve_url(url)
        self.assertEqual(result, [url])


# ---------------------------------------------------------------------------
# CashDrawerController.open_cash_drawer  (controlador legacy)
# ---------------------------------------------------------------------------


@tagged("post_install", "-at_install", "xtendoo_cash_drawer")
class TestCashDrawerController(TransactionCase):
    """Pruebas para el endpoint proxy legacy open_cash_drawer."""

    def setUp(self):
        super().setUp()
        self.controller = CashDrawerController()
        self._patch_target = f"{_CONTROLLER_MODULE}.http_requests.get"

    def _mock_get(self, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        return mock_resp

    def test_returns_error_when_no_url(self):
        """Sin URL debe retornar error sin llamar a requests.get."""
        with patch(self._patch_target) as mock_get:
            result = self.controller.open_cash_drawer(url="", api_key="")
        mock_get.assert_not_called()
        self.assertFalse(result["success"])
        self.assertIn("URL", result["error"])

    def test_returns_success_on_200_response(self):
        """Debe retornar success=True cuando el servicio responde 200."""
        with patch(self._patch_target, return_value=self._mock_get(200)):
            result = self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key=""
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertIsNone(result["error"])

    def test_resolved_url_is_present_on_success(self):
        """La respuesta de éxito debe incluir resolved_url."""
        url = "http://192.168.1.10:3211/open"
        with patch(self._patch_target, return_value=self._mock_get(200)):
            result = self.controller.open_cash_drawer(url=url, api_key="")
        self.assertEqual(result["resolved_url"], url)

    def test_api_key_sent_as_header(self):
        """Con API key se debe enviar la cabecera x-api-key."""
        with patch(self._patch_target, return_value=self._mock_get(200)) as mock_get:
            self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key="supersecret"
            )
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["x-api-key"], "supersecret")

    def test_no_api_key_header_when_empty(self):
        """Sin API key no se debe enviar la cabecera x-api-key."""
        with patch(self._patch_target, return_value=self._mock_get(200)) as mock_get:
            self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key=""
            )
        _, kwargs = mock_get.call_args
        self.assertNotIn("x-api-key", kwargs.get("headers", {}))

    def test_timeout_is_sent_to_requests(self):
        """La petición debe incluir el parámetro timeout."""
        with patch(self._patch_target, return_value=self._mock_get(200)) as mock_get:
            self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key=""
            )
        _, kwargs = mock_get.call_args
        self.assertIn("timeout", kwargs)

    def test_returns_error_on_connection_error(self):
        """Debe retornar error cuando hay ConnectionError."""
        import requests as req

        with patch(
            self._patch_target,
            side_effect=req.exceptions.ConnectionError("Connection refused"),
        ):
            result = self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key=""
            )
        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])

    def test_returns_error_on_timeout(self):
        """Debe retornar error cuando hay Timeout."""
        import requests as req

        with patch(self._patch_target, side_effect=req.exceptions.Timeout()):
            result = self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key=""
            )
        self.assertFalse(result["success"])
        self.assertIn("Tiempo de espera", result["error"])

    def test_localhost_error_includes_docker_hint(self):
        """El error para URL localhost debe incluir el hint de configuración Docker."""
        import requests as req

        with patch(self._patch_target, side_effect=req.exceptions.ConnectionError("Refused")):
            with patch(f"{_CONTROLLER_MODULE}._detect_docker_host_ip", return_value=None):
                result = self.controller.open_cash_drawer(
                    url="http://127.0.0.1:3211/open", api_key=""
                )
        self.assertFalse(result["success"])
        combined = (result.get("error") or "") + (result.get("resolved_url") or "")
        self.assertIn("127.0.0.1", combined)

    def test_tries_docker_candidate_before_original(self):
        """Con URL localhost debe intentar primero la URL con IP del host Docker."""
        import requests as req

        call_order = []

        def side_effect_get(url, **kwargs):
            call_order.append(url)
            raise req.exceptions.ConnectionError("Refused")

        with patch(self._patch_target, side_effect=side_effect_get):
            with patch(
                f"{_CONTROLLER_MODULE}._detect_docker_host_ip",
                return_value="172.17.0.1",
            ):
                self.controller.open_cash_drawer(url="http://127.0.0.1:3211/open", api_key="")

        self.assertGreater(len(call_order), 1)
        self.assertEqual(call_order[0], "http://172.17.0.1:3211/open")
        self.assertEqual(call_order[-1], "http://127.0.0.1:3211/open")

    def test_succeeds_on_second_candidate_url(self):
        """Debe tener éxito con la segunda URL candidata si la primera falla."""
        import requests as req

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        attempt = [0]

        def side_effect_get(url, **kwargs):
            attempt[0] += 1
            if attempt[0] == 1:
                raise req.exceptions.ConnectionError("First failed")
            return mock_resp

        with patch(self._patch_target, side_effect=side_effect_get):
            with patch(
                f"{_CONTROLLER_MODULE}._detect_docker_host_ip",
                return_value="172.17.0.1",
            ):
                result = self.controller.open_cash_drawer(
                    url="http://127.0.0.1:3211/open", api_key=""
                )
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)

    def test_non_200_response_still_returns_success(self):
        """Una respuesta HTTP != 200 del cajón también se reporta como éxito (conexión OK)."""
        with patch(self._patch_target, return_value=self._mock_get(404)):
            result = self.controller.open_cash_drawer(
                url="http://192.168.1.10:3211/open", api_key=""
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 404)


# ---------------------------------------------------------------------------
# pos.config — nuevos campos del bridge local
# ---------------------------------------------------------------------------


@tagged("post_install", "-at_install", "xtendoo_cash_drawer")
class TestPosConfigCashDrawer(TransactionCase):
    """Pruebas para los campos del cajón en pos.config (nueva arquitectura)."""

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {"name": "Test POS Cajón", "company_id": self.env.company.id}
        )

    # --- cash_drawer_use_bridge ---

    def test_cash_drawer_use_bridge_default_is_false(self):
        """El campo cash_drawer_use_bridge debe tener valor False por defecto."""
        self.assertFalse(self.pos_config.cash_drawer_use_bridge)

    def test_cash_drawer_use_bridge_can_be_enabled(self):
        """Debe poder activar cash_drawer_use_bridge."""
        self.pos_config.cash_drawer_use_bridge = True
        self.assertTrue(self.pos_config.cash_drawer_use_bridge)

    # --- cash_drawer_bridge_url ---

    def test_cash_drawer_bridge_url_default_value(self):
        """El campo cash_drawer_bridge_url debe tener URL por defecto."""
        self.assertEqual(self.pos_config.cash_drawer_bridge_url, "http://127.0.0.1:3211")

    def test_cash_drawer_bridge_url_can_be_changed(self):
        """Debe poder cambiar cash_drawer_bridge_url a una IP LAN."""
        self.pos_config.cash_drawer_bridge_url = "http://192.168.1.50:3211"
        self.assertEqual(self.pos_config.cash_drawer_bridge_url, "http://192.168.1.50:3211")

    # --- cash_drawer_printer_name ---

    def test_cash_drawer_printer_name_field_exists(self):
        """El campo cash_drawer_printer_name debe existir y almacenarse."""
        self.pos_config.cash_drawer_printer_name = "POS-80C"
        self.assertEqual(self.pos_config.cash_drawer_printer_name, "POS-80C")

    # --- cash_drawer_api_key ---

    def test_cash_drawer_api_key_field_exists(self):
        """El campo cash_drawer_api_key debe existir y almacenarse."""
        self.pos_config.cash_drawer_api_key = "mysecretkey"
        self.assertEqual(self.pos_config.cash_drawer_api_key, "mysecretkey")

    # --- cash_drawer_auto_open ---

    def test_cash_drawer_auto_open_default_is_true(self):
        """El campo cash_drawer_auto_open debe tener valor True por defecto."""
        self.assertTrue(self.pos_config.cash_drawer_auto_open)

    def test_cash_drawer_auto_open_can_be_set_to_false(self):
        """Debe poder desactivar cash_drawer_auto_open."""
        self.pos_config.cash_drawer_auto_open = False
        self.assertFalse(self.pos_config.cash_drawer_auto_open)

    def test_cash_drawer_auto_open_can_be_reenabled(self):
        """Debe poder reactivar cash_drawer_auto_open tras desactivarlo."""
        self.pos_config.cash_drawer_auto_open = False
        self.pos_config.cash_drawer_auto_open = True
        self.assertTrue(self.pos_config.cash_drawer_auto_open)

    # --- cash_drawer_open_url (campo legacy) ---

    def test_cash_drawer_open_url_legacy_field_exists(self):
        """El campo legacy cash_drawer_open_url debe existir y almacenarse."""
        url = "http://192.168.1.10:3211/open"
        self.pos_config.cash_drawer_open_url = url
        self.assertEqual(self.pos_config.cash_drawer_open_url, url)

    # --- _compute_effective_bridge_url ---

    def test_effective_url_uses_bridge_url_when_set(self):
        """effective_bridge_url debe devolver cash_drawer_bridge_url si está relleno."""
        self.pos_config.cash_drawer_bridge_url = "http://192.168.1.50:3211"
        self.pos_config.cash_drawer_open_url = "http://legacy.url/open"
        self.assertEqual(self.pos_config.cash_drawer_effective_url, "http://192.168.1.50:3211")

    def test_effective_url_falls_back_to_open_url(self):
        """effective_bridge_url debe usar cash_drawer_open_url como fallback cuando bridge_url está vacío."""
        self.pos_config.cash_drawer_bridge_url = False
        self.pos_config.cash_drawer_open_url = "http://legacy.url/open"
        self.assertEqual(self.pos_config.cash_drawer_effective_url, "http://legacy.url/open")

    def test_effective_url_empty_when_both_empty(self):
        """effective_bridge_url debe ser cadena vacía si ambos campos están vacíos."""
        self.pos_config.cash_drawer_bridge_url = False
        self.pos_config.cash_drawer_open_url = False
        self.assertEqual(self.pos_config.cash_drawer_effective_url, "")

    # --- action_test_cash_drawer ---

    def test_action_test_cash_drawer_returns_client_action_with_bridge_params(self):
        """action_test_cash_drawer debe retornar una acción cliente con los nuevos parámetros."""
        self.pos_config.cash_drawer_bridge_url = "http://192.168.1.10:3211"
        self.pos_config.cash_drawer_printer_name = "POS-80C"
        self.pos_config.cash_drawer_api_key = "mykey"

        action = self.pos_config.action_test_cash_drawer()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "xtendoo_cash_drawer_open_test")
        self.assertEqual(action["params"]["bridge_url"], "http://192.168.1.10:3211")
        self.assertEqual(action["params"]["printer_name"], "POS-80C")
        self.assertEqual(action["params"]["api_key"], "mykey")

    def test_action_test_cash_drawer_raises_when_no_url_configured(self):
        """action_test_cash_drawer debe lanzar UserError si no hay URL efectiva configurada."""
        self.pos_config.cash_drawer_bridge_url = False
        self.pos_config.cash_drawer_open_url = False
        with self.assertRaises(UserError):
            self.pos_config.action_test_cash_drawer()

    def test_action_test_cash_drawer_uses_legacy_url_as_fallback(self):
        """action_test_cash_drawer debe funcionar si solo hay cash_drawer_open_url (legado)."""
        self.pos_config.cash_drawer_bridge_url = False
        self.pos_config.cash_drawer_open_url = "http://legacy.url/open"
        # No debe lanzar UserError
        action = self.pos_config.action_test_cash_drawer()
        self.assertEqual(action["type"], "ir.actions.client")

    def test_action_test_cash_drawer_empty_api_key(self):
        """api_key debe ser cadena vacía en la acción cuando no está configurada."""
        self.pos_config.cash_drawer_bridge_url = "http://192.168.1.10:3211"
        self.pos_config.cash_drawer_api_key = False

        action = self.pos_config.action_test_cash_drawer()
        self.assertEqual(action["params"]["api_key"], "")

    def test_multiple_configs_have_independent_use_bridge(self):
        """Cada pos.config debe tener su propio valor de cash_drawer_use_bridge."""
        config2 = self.env["pos.config"].create(
            {"name": "Test POS Cajón 2", "company_id": self.env.company.id}
        )
        self.pos_config.cash_drawer_use_bridge = True
        self.assertTrue(self.pos_config.cash_drawer_use_bridge)
        self.assertFalse(config2.cash_drawer_use_bridge)


# ---------------------------------------------------------------------------
# Assets POS — regresión del canal de apertura
# ---------------------------------------------------------------------------


@tagged("post_install", "-at_install", "xtendoo_cash_drawer")
class TestPosAssetsCashDrawer(TransactionCase):
    """Garantiza que el TPV usa el mismo canal directo que la prueba de configuración."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._module_root = Path(__file__).resolve().parents[1]

    def _read_asset(self, relative_path):
        return (self._module_root / relative_path).read_text(encoding="utf-8")

    def test_control_buttons_use_direct_bridge_request(self):
        """El botón principal del POS debe abrir el cajón desde el navegador."""
        source = self._read_asset(Path("static/src/js/cash_drawer_button.js"))
        self.assertIn("sendCashDrawerRequest", source)
        self.assertNotIn("sendCashDrawerViaProxy", source)

    def test_navbar_button_uses_direct_bridge_request(self):
        """El botón del navbar debe usar la misma apertura directa que configuración."""
        source = self._read_asset(Path("static/src/js/cash_drawer_navbar_button.js"))
        self.assertIn("sendCashDrawerRequest", source)
        self.assertNotIn("sendCashDrawerViaProxy", source)

    def test_payment_screen_auto_open_uses_direct_bridge_request(self):
        """La autoapertura en pagos debe mantenerse en el navegador, no en Python."""
        source = self._read_asset(Path("static/src/js/cash_drawer_payment.js"))
        self.assertIn("sendCashDrawerRequest(cfg)", source)
        self.assertNotIn("sendCashDrawerViaProxy", source)


# ---------------------------------------------------------------------------
# res.config.settings — campos relacionados
# ---------------------------------------------------------------------------


@tagged("post_install", "-at_install", "xtendoo_cash_drawer")
class TestResConfigSettingsCashDrawer(TransactionCase):
    """Pruebas para los campos relacionados en res.config.settings."""

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {"name": "Test POS Settings", "company_id": self.env.company.id}
        )

    def _create_settings(self):
        return self.env["res.config.settings"].create(
            {"pos_config_id": self.pos_config.id}
        )

    def test_pos_cash_drawer_use_bridge_related_reads_pos_config(self):
        """pos_cash_drawer_use_bridge debe reflejar el valor de pos.config."""
        self.pos_config.cash_drawer_use_bridge = True
        settings = self._create_settings()
        self.assertTrue(settings.pos_cash_drawer_use_bridge)

    def test_pos_cash_drawer_bridge_url_related_reads_pos_config(self):
        """pos_cash_drawer_bridge_url debe reflejar el valor de pos.config."""
        self.pos_config.cash_drawer_bridge_url = "http://192.168.1.10:3211"
        settings = self._create_settings()
        self.assertEqual(settings.pos_cash_drawer_bridge_url, "http://192.168.1.10:3211")

    def test_pos_cash_drawer_printer_name_related_reads_pos_config(self):
        """pos_cash_drawer_printer_name debe reflejar el valor de pos.config."""
        self.pos_config.cash_drawer_printer_name = "STAR TSP100"
        settings = self._create_settings()
        self.assertEqual(settings.pos_cash_drawer_printer_name, "STAR TSP100")

    def test_pos_cash_drawer_auto_open_defaults_to_true(self):
        """El campo relacionado debe reflejar el valor True por defecto."""
        settings = self._create_settings()
        self.assertTrue(settings.pos_cash_drawer_auto_open)

    def test_pos_cash_drawer_auto_open_propagates_to_pos_config(self):
        """Cambiar pos_cash_drawer_auto_open y ejecutar debe actualizar pos.config."""
        settings = self._create_settings()
        settings.pos_cash_drawer_auto_open = False
        settings.execute()
        self.assertFalse(self.pos_config.cash_drawer_auto_open)

    def test_pos_cash_drawer_bridge_url_propagates_to_pos_config(self):
        """Cambiar pos_cash_drawer_bridge_url y ejecutar debe actualizar pos.config."""
        settings = self._create_settings()
        settings.pos_cash_drawer_bridge_url = "http://192.168.1.99:3211"
        settings.execute()
        self.assertEqual(self.pos_config.cash_drawer_bridge_url, "http://192.168.1.99:3211")

    def test_action_test_cash_drawer_delegates_to_pos_config(self):
        """action_test_cash_drawer en settings debe delegar a pos.config."""
        self.pos_config.cash_drawer_bridge_url = "http://192.168.1.10:3211"
        settings = self._create_settings()

        action = settings.action_test_cash_drawer()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["params"]["bridge_url"], "http://192.168.1.10:3211")

    def test_action_test_cash_drawer_raises_when_no_url_in_settings(self):
        """action_test_cash_drawer debe lanzar UserError si pos.config no tiene URL."""
        self.pos_config.cash_drawer_bridge_url = False
        self.pos_config.cash_drawer_open_url = False
        settings = self._create_settings()

        with self.assertRaises(UserError):
            settings.action_test_cash_drawer()

    def test_legacy_open_url_field_is_accessible_via_settings(self):
        """El campo legacy pos_cash_drawer_open_url debe ser accesible desde settings."""
        self.pos_config.cash_drawer_open_url = "http://legacy.url/open"
        settings = self._create_settings()
        self.assertEqual(settings.pos_cash_drawer_open_url, "http://legacy.url/open")
