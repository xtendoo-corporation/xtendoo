# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Controlador proxy del cajón portamonedas.

Arquitectura: navegador → Odoo (proxy) → bridge local
------------------------------------------------------
Este controlador es la VÍA PRINCIPAL de apertura del cajón desde Odoo 17+.

Flujo de red:
  1. El navegador del TPV envía POST /xtendoo_cash_drawer/open a Odoo.
     → Mismo origen que Odoo: CERO problemas de CORS.
  2. Odoo (Python) reenvía la petición GET al bridge local por IP LAN.
     → Llamada servidor-a-servidor: CERO problemas de CORS.

Esto resuelve definitivamente el problema CORS que aparece cuando el
bridge local (ejecutable en Windows/Linux del cajero) no puede añadir
cabeceras Access-Control-Allow-Origin porque es un binario externo.

Endpoints:
  POST /xtendoo_cash_drawer/open   → proxy apertura del cajón
  POST /xtendoo_cash_drawer/health → proxy health check del bridge
"""

import re
import socket
import logging

import requests as http_requests

from odoo import http

_logger = logging.getLogger(__name__)

# Patrón para detectar referencias al host local en la URL configurada
_LOCALHOST_RE = re.compile(r"\b(127\.0\.0\.1|localhost)\b", re.I)

# Tiempo máximo de espera al cajón (segundos)
_TIMEOUT = 5


def _detect_docker_host_ip():
    """
    Intenta averiguar la IP del host desde dentro del contenedor Docker.

    Devuelve la primera IP que resuelva o None si no estamos en Docker.
    """
    # 1) host.docker.internal (Mac / Windows Docker Desktop; Linux con extra_hosts)
    try:
        ip = socket.gethostbyname("host.docker.internal")
        _logger.debug("[CashDrawer] host.docker.internal → %s", ip)
        return ip
    except OSError:
        pass

    # 2) Puerta de enlace predeterminada desde /proc/net/route (Linux)
    try:
        with open("/proc/net/route") as fh:
            for line in fh:
                parts = line.split()
                # Destino 00000000 = ruta por defecto
                if len(parts) >= 3 and parts[1] == "00000000":
                    gateway_hex = parts[2]
                    # La IP está en little-endian hexadecimal
                    ip = socket.inet_ntoa(bytes.fromhex(gateway_hex)[::-1])
                    _logger.debug("[CashDrawer] Gateway /proc/net/route → %s", ip)
                    return ip
    except Exception:  # noqa: BLE001
        pass

    return None


def _resolve_url(url: str) -> list[str]:
    """
    Devuelve una lista de URLs a probar (de más específica a más genérica).

    Si la URL referencia localhost o 127.0.0.1 genera versiones alternativas
    con la IP del host Docker para que funcione dentro del contenedor.
    """
    if not _LOCALHOST_RE.search(url):
        return [url]

    candidates = []
    host_ip = _detect_docker_host_ip()
    if host_ip:
        candidates.append(_LOCALHOST_RE.sub(host_ip, url))

    # Siempre añadimos la URL original como último recurso (dev sin Docker)
    candidates.append(url)

    return candidates


class CashDrawerController(http.Controller):
    """
    Endpoints proxy para el cajón portamonedas.

    El navegador llama a estos endpoints en el mismo servidor Odoo (sin CORS).
    Odoo reenvía la petición al bridge local por IP LAN (sin CORS).
    """

    # ------------------------------------------------------------------
    # Apertura del cajón
    # ------------------------------------------------------------------

    @http.route(
        "/xtendoo_cash_drawer/open",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def open_cash_drawer(self, url: str = "", api_key: str = "", **_kwargs):
        """
        Proxy que envía la señal de apertura al cajón portamonedas.

        Parámetros JSON:
            url     (str): URL completa del endpoint de apertura del bridge.
                           Ejemplo: http://192.168.18.7:3210/open-drawer?printer=POS-80C
            api_key (str): Clave API (se envía como cabecera x-api-key).

        Respuesta JSON:
            {success: bool, status_code: int|None, error: str|None, resolved_url: str}
        """
        if not url:
            return {"success": False, "error": "No hay URL configurada para el cajón."}

        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        urls_to_try = _resolve_url(url)
        last_error = None

        for candidate_url in urls_to_try:
            _logger.info("[CashDrawer] Probando URL: %s", candidate_url)
            try:
                resp = http_requests.get(candidate_url, headers=headers, timeout=_TIMEOUT)
                _logger.info(
                    "[CashDrawer] Respuesta %s desde %s",
                    resp.status_code,
                    candidate_url,
                )
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "resolved_url": candidate_url,
                    "error": None,
                }
            except http_requests.exceptions.ConnectionError as exc:
                last_error = str(exc)
                _logger.warning(
                    "[CashDrawer] ConnectionError en %s: %s",
                    candidate_url,
                    exc,
                )
            except http_requests.exceptions.Timeout:
                last_error = f"Tiempo de espera agotado ({_TIMEOUT}s) en {candidate_url}"
                _logger.warning("[CashDrawer] Timeout en %s", candidate_url)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                _logger.exception(
                    "[CashDrawer] Error inesperado en %s", candidate_url
                )

        hint = ""
        if _LOCALHOST_RE.search(url):
            hint = (
                " — El bridge parece escuchar sólo en 127.0.0.1 del host. "
                "Para que Odoo (Docker) pueda alcanzarlo, configura el bridge para "
                "escuchar en 0.0.0.0, o añade 'extra_hosts: [host.docker.internal:host-gateway]' "
                "en docker-compose."
            )
        return {
            "success": False,
            "status_code": None,
            "resolved_url": urls_to_try[-1],
            "error": (last_error or "Error desconocido") + hint,
        }

    # ------------------------------------------------------------------
    # Health check del bridge
    # ------------------------------------------------------------------

    @http.route(
        "/xtendoo_cash_drawer/health",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def health_check_cash_drawer(self, url: str = "", **_kwargs):
        """
        Proxy para verificar el estado del bridge (GET /health).

        Parámetros JSON:
            url (str): URL del endpoint /health del bridge.

        Respuesta JSON:
            {available: bool, detail: str, resolved_url: str|None}
        """
        if not url:
            return {"available": False, "detail": "No hay URL configurada.", "resolved_url": None}

        urls_to_try = _resolve_url(url)
        last_error = "No se pudo conectar"

        for candidate_url in urls_to_try:
            _logger.info("[CashDrawer] Health check en: %s", candidate_url)
            try:
                resp = http_requests.get(candidate_url, timeout=3)
                if resp.ok:
                    detail = "Bridge disponible"
                    try:
                        data = resp.json()
                        if data.get("status"):
                            detail = f"Bridge disponible (status: {data['status']})"
                    except Exception:  # noqa: BLE001
                        pass
                    return {"available": True, "detail": detail, "resolved_url": candidate_url}
                else:
                    return {
                        "available": False,
                        "detail": f"Bridge no disponible (HTTP {resp.status_code})",
                        "resolved_url": candidate_url,
                    }
            except http_requests.exceptions.ConnectionError as exc:
                last_error = str(exc)
                _logger.debug("[CashDrawer] Health ConnectionError en %s: %s", candidate_url, exc)
            except http_requests.exceptions.Timeout:
                last_error = f"Tiempo de espera agotado en {candidate_url}"
                _logger.debug("[CashDrawer] Health Timeout en %s", candidate_url)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                _logger.debug("[CashDrawer] Health error en %s: %s", candidate_url, exc)

        return {"available": False, "detail": last_error, "resolved_url": None}

