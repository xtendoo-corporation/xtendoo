#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cash_drawer_proxy.py — Proxy local para apertura de cajón portamonedas en Windows
==================================================================================
Script ligero que expone un endpoint HTTP en localhost:7070 para que el TPV de
Odoo (que corre en el navegador) pueda abrir el cajón portamonedas via USB/serie
en el PC del usuario, sin necesidad de IoT Box ni WebUSB.

Uso:
    python cash_drawer_proxy.py [--port 7070] [--printer "EPSON TM-T20"]

Endpoints:
    POST /open_cashbox
        Body: JSON  { "printer_name": "...", "command_bytes": [27, 112, 0, 25, 250] }
        (ambos campos opcionales; si se omiten se usan los valores por defecto)
        Respuesta: { "ok": true } o { "ok": false, "error": "..." }

    GET  /status
        Respuesta: { "ok": true, "printers": ["EPSON TM-T20", ...] }

Dependencias:
    pip install pywin32        (para win32print, recomendado)
    pip install pyinstaller    (para generar .exe, opcional)

Nota de seguridad:
    El servidor solo acepta conexiones de localhost (127.0.0.1).
    Añade una excepción en el firewall de Windows si el navegador y el
    proxy corren en máquinas distintas (no recomendado).
"""

import argparse
import json
import logging
import platform
import subprocess
import sys
import tempfile
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

__version__ = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("cash_drawer_proxy")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEFAULT_PORT    = 7070
DEFAULT_COMMAND = bytes([0x1B, 0x70, 0x00, 0x19, 0xFA])  # ESC p pin 2

_IS_WINDOWS = platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Detección de impresoras
# ---------------------------------------------------------------------------

def detect_printers():
    """Devuelve una lista de nombres de impresoras instaladas."""
    if _IS_WINDOWS:
        try:
            import win32print
            return [p[2] for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )]
        except ImportError:
            pass
        # Fallback: PowerShell
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Printer | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=8,
            )
            if r.returncode == 0:
                return [l.strip() for l in r.stdout.splitlines() if l.strip()]
        except Exception:
            pass
    return []


# ---------------------------------------------------------------------------
# Envío del comando ESC/POS
# ---------------------------------------------------------------------------

def send_escpos(printer_name, command_bytes):
    """Envía command_bytes a la impresora Windows indicada.

    Intenta win32print primero; si no está disponible, usa copy /b.

    Returns:
        True si tuvo éxito.
    Raises:
        RuntimeError si falló.
    """
    if not _IS_WINDOWS:
        raise RuntimeError("Este proxy solo funciona en Windows.")

    # win32print
    try:
        import win32print
        hp = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(hp, 1, ("CashDrawer", None, "RAW"))
            try:
                win32print.StartPagePrinter(hp)
                win32print.WritePrinter(hp, command_bytes)
                win32print.EndPagePrinter(hp)
            finally:
                win32print.EndDocPrinter(hp)
        finally:
            win32print.ClosePrinter(hp)
        _log.info("Cajón abierto via win32print: %s", printer_name)
        return True
    except ImportError:
        _log.debug("win32print no disponible, usando copy /b")
    except Exception as exc:
        raise RuntimeError("win32print: %s" % exc) from exc

    # copy /b fallback
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(command_bytes)
            tmp = f.name
        dest = printer_name if printer_name.startswith("\\\\") \
            else "\\\\.\\%s" % printer_name
        r = subprocess.run(
            ["cmd", "/c", "copy", "/b", tmp, dest],
            capture_output=True, timeout=5,
        )
        if r.returncode != 0:
            raise RuntimeError(
                "copy /b devolvió %d: %s" % (
                    r.returncode,
                    r.stderr.decode(errors="replace").strip(),
                )
            )
        _log.info("Cajón abierto via copy /b: %s", printer_name)
        return True
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    """Manejador HTTP mínimo para los endpoints del proxy."""

    # Nombre de impresora por defecto (se sobreescribe con --printer)
    default_printer: str = ""

    def log_message(self, fmt, *args):  # silenciar el log por defecto
        _log.debug(fmt, *args)

    def _send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # CORS: permitir origen del TPV de Odoo
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # preflight CORS
        self._send_json(200, {})

    def do_GET(self):
        if self.path == "/status":
            printers = detect_printers()
            self._send_json(200, {
                "ok": True,
                "version": __version__,
                "default_printer": self.__class__.default_printer,
                "printers": printers,
            })
        else:
            self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self):
        if self.path != "/open_cashbox":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        # Leer body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        printer_name = (
            payload.get("printer_name")
            or self.__class__.default_printer
        )
        raw_bytes = payload.get("command_bytes")

        if raw_bytes:
            command = bytes(raw_bytes)
        else:
            command = DEFAULT_COMMAND

        if not printer_name:
            printers = detect_printers()
            if printers:
                printer_name = printers[0]
                _log.info(
                    "No se especificó impresora; usando la primera detectada: %s",
                    printer_name,
                )
            else:
                self._send_json(400, {
                    "ok": False,
                    "error": (
                        "No se encontró ninguna impresora. "
                        "Usa --printer al iniciar el proxy o "
                        "pasa 'printer_name' en el body."
                    ),
                })
                return

        try:
            send_escpos(printer_name, command)
            self._send_json(200, {"ok": True, "printer": printer_name})
        except RuntimeError as exc:
            _log.error("Error al abrir el cajón: %s", exc)
            self._send_json(500, {"ok": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Proxy local para apertura de cajón portamonedas (Windows)"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help="Puerto en el que escucha el proxy (por defecto: %d)" % DEFAULT_PORT,
    )
    parser.add_argument(
        "--printer", default="",
        help="Nombre de la impresora por defecto (p. ej. 'EPSON TM-T20')",
    )
    args = parser.parse_args()

    if not _IS_WINDOWS:
        _log.warning(
            "⚠️  Este proxy está diseñado para Windows. "
            "En Linux/macOS usa directamente la integración CUPS/dispositivo de Odoo."
        )

    _Handler.default_printer = args.printer

    server = HTTPServer(("127.0.0.1", args.port), _Handler)
    _log.info(
        "🚀 Cash Drawer Proxy v%s iniciado en http://localhost:%d",
        __version__, args.port,
    )
    if args.printer:
        _log.info("   Impresora por defecto: %s", args.printer)
    else:
        printers = detect_printers()
        if printers:
            _log.info(
                "   Impresoras detectadas: %s",
                ", ".join(printers[:5]),
            )
        else:
            _log.warning("   No se detectaron impresoras. ¿pywin32 instalado?")

    _log.info("   Pulsa Ctrl+C para detener.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log.info("Proxy detenido.")
        server.server_close()


if __name__ == "__main__":
    main()
