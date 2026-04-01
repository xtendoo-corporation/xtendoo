# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Controlador proxy para el cajón portamonedas.

El navegador no puede enviar cabeceras personalizadas (x-api-key) a servicios
de terceros sin que éstos soporten CORS. Este endpoint actúa como proxy:
el navegador llama a Odoo (mismo origen → sin CORS) y Odoo realiza la
petición al cajón desde Python, sin restricciones de CORS.

Resolución de 127.0.0.1 en entornos Docker
-------------------------------------------
Dentro del contenedor, 127.0.0.1 apunta al propio contenedor, no al host.
El controlador intenta automáticamente varias estrategias para alcanzar
el servicio en el host:

  1. host.docker.internal  (requiere extra_hosts en docker-compose)
  2. IP de la puerta de enlace leída de /proc/net/route
  3. URL sin sustitución (funciona en entornos sin Docker / dev local)

Para que la estrategia 2 funcione el servicio del cajón DEBE escuchar en
0.0.0.0 (no sólo en 127.0.0.1). Si escucha sólo en loopback, añade al
servicio Docker:

    extra_hosts:
      - "host.docker.internal:host-gateway"

y configura el servicio del cajón para escuchar en 0.0.0.0.
"""

import re
import socket
import logging

import requests as http_requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Patrón para detectar referencias al host local en la URL configurada
_LOCALHOST_RE = re.compile(r'\b(127\.0\.0\.1|localhost)\b', re.I)

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

    @http.route(
        "/xtendoo_cash_drawer/open",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def open_cash_drawer(self, url: str = "", api_key: str = "", **_kwargs):
        """
        Proxy que envía la señal de apertura al cajón portamonedas.

        Parámetros JSON:
            url     (str): URL completa del servicio del cajón.
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
                _logger.info("[CashDrawer] Respuesta %s desde %s", resp.status_code, candidate_url)
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "resolved_url": candidate_url,
                    "error": None,
                }
            except http_requests.exceptions.ConnectionError as exc:
                last_error = str(exc)
                _logger.warning("[CashDrawer] ConnectionError en %s: %s", candidate_url, exc)
            except http_requests.exceptions.Timeout:
                last_error = f"Tiempo de espera agotado ({_TIMEOUT}s) en {candidate_url}"
                _logger.warning("[CashDrawer] Timeout en %s", candidate_url)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                _logger.exception("[CashDrawer] Error inesperado en %s", candidate_url)

        # Ninguna URL funcionó
        hint = ""
        if _LOCALHOST_RE.search(url):
            hint = (
                " — El servicio del cajón parece escuchar sólo en 127.0.0.1 del host. "
                "Para que Odoo (Docker) pueda alcanzarlo, configura el servicio para "
                "escuchar en 0.0.0.0, o añade 'extra_hosts: [host.docker.internal:host-gateway]' "
                "en docker-compose."
            )
        return {
            "success": False,
            "status_code": None,
            "resolved_url": urls_to_try[-1],
            "error": (last_error or "Error desconocido") + hint,
        }

