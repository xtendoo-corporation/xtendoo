# -*- coding: utf-8 -*-
"""Utilidades compartidas para apertura de cajón portamonedas.

Contiene las funciones puras (sin dependencia de modelos Odoo) que son
utilizadas tanto por ``res.config.settings`` como por ``pos.config``.
"""
import logging
import os
import platform
import re
import socket
import subprocess
import tempfile

_logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

# Comando ESC/POS de apertura de cajón por defecto: bytes 27 (ESC) y 105 (i)
CASH_DRAWER_COMMAND = bytes([27, 105])

# Patrones de ficheros de dispositivo locales en Linux
DEVICE_PATTERNS = [
    "/dev/lp*",
    "/dev/ttyS[0-9]*",
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/usb/lp*",
]

# Expresión regular para detectar el formato "host:puerto"
TCP_RE = re.compile(r"^([\w.\-]+):(\d{1,5})$")


# ---------------------------------------------------------------------------
# Detección de impresoras
# ---------------------------------------------------------------------------

def detect_windows_printers():
    """Devuelve lista de (nombre, etiqueta) con las impresoras instaladas en Windows.

    Primero intenta PowerShell (Get-Printer), con fallback a wmic.
    """
    printers = []

    # Intento 1: PowerShell Get-Printer (Windows 8+ / Server 2012+)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=8,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            for name in result.stdout.splitlines():
                name = name.strip()
                if name:
                    printers.append((name, "\U0001f5a8 %s (Windows)" % name))
            if printers:
                return printers
    except Exception as exc:
        _logger.debug("PowerShell Get-Printer no disponible: %s", exc)

    # Intento 2: wmic (compatible con Windows 7+)
    try:
        result = subprocess.run(
            ["wmic", "printer", "get", "name"],
            capture_output=True, text=True, timeout=8,
            encoding="cp1252", errors="replace",
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines()[1:]:
                name = line.strip()
                if name:
                    printers.append((name, "\U0001f5a8 %s (Windows)" % name))
    except Exception as exc:
        _logger.debug("wmic no disponible: %s", exc)

    return printers


def get_docker_gateway():
    """Devuelve la IP de la gateway del contenedor Docker (= host Linux)."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=2,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Envío de comandos
# ---------------------------------------------------------------------------

def send_windows_printer(printer_name, command):
    """Envía ``command`` (bytes) directamente a una impresora Windows.

    Intenta win32print (pywin32) primero; si no está disponible, usa
    un fichero temporal con «copy /b».

    Devuelve True si tuvo éxito, lanza OSError/RuntimeError si falló.
    """
    # Intento 1: win32print (requiere pywin32)
    try:
        import win32print  # noqa: PLC0415
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            hjob = win32print.StartDocPrinter(
                hprinter, 1, ("CashDrawer", None, "RAW")
            )
            try:
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, command)
                win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
        return True
    except ImportError:
        _logger.debug("win32print no disponible, usando fallback copy /b")
    except Exception as exc:
        raise OSError(str(exc)) from exc

    # Intento 2: copy /b <tmpfile> "\\.\<impresora>" (RAW)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(command)
            tmp_path = tmp.name
        dest = printer_name if printer_name.startswith("\\\\") \
            else "\\\\.\\%s" % printer_name
        result = subprocess.run(
            ["cmd", "/c", "copy", "/b", tmp_path, dest],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0:
            raise OSError(
                result.stderr.decode(errors="replace").strip()
                or "copy /b devolvió código %d" % result.returncode
            )
        return True
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def parse_command_bytes(raw_bytes_str):
    """Parsea una cadena de bytes decimales separados por espacios.

    Args:
        raw_bytes_str: cadena como "27 112 0 25 250"
    Returns:
        bytes object
    Raises:
        ValueError si el formato no es válido
    """
    if not raw_bytes_str or not raw_bytes_str.strip():
        return CASH_DRAWER_COMMAND
    parts = raw_bytes_str.strip().split()
    result = bytes(int(b) for b in parts if b.strip())
    if not result:
        raise ValueError("Cadena de bytes vacía")
    return result


def open_cash_drawer(printer_path, command_bytes_str=None):
    """Intenta abrir el cajón portamonedas.

    Cascade de intentos:
      0. Impresora Windows (solo en servidor Windows, formato no TCP)
      1. Socket TCP directo (formato host:puerto)
      2. lpr contra el host Docker
      3. lpr local
      4. Escritura directa al dispositivo

    Args:
        printer_path: IP:port, nombre CUPS o ruta de dispositivo
        command_bytes_str: string de bytes decimales, p.ej. "27 112 0 25 250"

    Returns:
        True si se abrió con éxito

    Raises:
        RuntimeError con detalle de todos los errores si falló
    """
    try:
        command = parse_command_bytes(command_bytes_str)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "Comando de apertura no válido: %r — %s" % (command_bytes_str, exc)
        ) from exc

    errors = []
    tcp_match = TCP_RE.match(printer_path)

    # --- Intento 0: impresora Windows ---
    if _IS_WINDOWS and not tcp_match:
        try:
            send_windows_printer(printer_path, command)
            _logger.info("Cajón abierto via impresora Windows: %s", printer_path)
            return True
        except Exception as exc:
            _logger.warning("Windows printer %s falló: %s", printer_path, exc)
            errors.append("Windows %s: %s" % (printer_path, exc))

    # --- Intento 1: socket TCP directo ---
    if tcp_match:
        host, port = tcp_match.group(1), int(tcp_match.group(2))
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                sock.sendall(command)
            _logger.info("Cajón abierto via TCP %s:%s", host, port)
            return True
        except OSError as exc:
            _logger.warning("TCP %s:%s falló: %s", host, port, exc)
            errors.append("TCP %s:%s → %s" % (host, port, exc))

    # Preparar fichero temporal para los intentos lpr
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(command)
            tmp_path = tmp.name

        # --- Intento 2: lpr contra el host Docker ---
        if not tcp_match:
            gateway = get_docker_gateway()
            if gateway:
                try:
                    result = subprocess.run(
                        ["lpr", "-h", gateway, "-l", "-P", printer_path, tmp_path],
                        capture_output=True, timeout=5,
                    )
                    if result.returncode == 0:
                        _logger.info(
                            "Cajón abierto via lpr en host %s, cola %s",
                            gateway, printer_path,
                        )
                        return True
                    stderr = result.stderr.decode(errors="replace").strip()
                    errors.append(
                        "lpr -h %s -P %s: %s" % (
                            gateway, printer_path, stderr or result.returncode
                        )
                    )
                except FileNotFoundError:
                    errors.append("Comando lpr no encontrado en el sistema.")
                except Exception as exc:
                    errors.append(str(exc))

        # --- Intento 3: lpr local ---
        if not tcp_match:
            try:
                result = subprocess.run(
                    ["lpr", "-l", "-P", printer_path, tmp_path],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    _logger.info(
                        "Cajón abierto via lpr local, cola %s", printer_path
                    )
                    return True
                stderr = result.stderr.decode(errors="replace").strip()
                errors.append(
                    "lpr -P %s: %s" % (printer_path, stderr or result.returncode)
                )
            except FileNotFoundError:
                pass
            except subprocess.TimeoutExpired:
                errors.append("Tiempo de espera agotado (lpr).")
            except Exception as exc:
                errors.append(str(exc))
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # --- Intento 4: escritura directa al dispositivo ---
    if (not tcp_match
            and os.path.exists(printer_path)
            and not os.path.isdir(printer_path)):
        try:
            with open(printer_path, "wb") as dev:
                dev.write(command)
            _logger.info("Cajón abierto via dispositivo: %s", printer_path)
            return True
        except OSError as exc:
            errors.append("Dispositivo %s: %s" % (printer_path, exc))

    raise RuntimeError(
        "No se pudo abrir el cajón portamonedas.\n"
        "Destino: %s\n\nErrores:\n%s"
        % (printer_path, "\n".join(errors) or "Error desconocido")
    )

