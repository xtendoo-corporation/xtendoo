# -*- coding: utf-8 -*-
import glob
import logging
import os
import platform
import re
import socket
import subprocess
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

# Comando ESC/POS de apertura de cajón por defecto: bytes 27 (ESC) y 105 (i)
_CASH_DRAWER_COMMAND = bytes([27, 105])

# Patrones de ficheros de dispositivo locales en Linux (paralelo / serie)
_DEVICE_PATTERNS = [
    "/dev/lp*",
    "/dev/ttyS[0-9]*",
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/usb/lp*",
]

# Expresión regular para detectar el formato "host:puerto"
_TCP_RE = re.compile(r"^([\w.\-]+):(\d{1,5})$")


def _detect_windows_printers():
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
                    printers.append((name, u"\U0001f5a8 %s (Windows)" % name))
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
            for line in result.stdout.splitlines()[1:]:   # saltar cabecera
                name = line.strip()
                if name:
                    printers.append((name, u"\U0001f5a8 %s (Windows)" % name))
    except Exception as exc:
        _logger.debug("wmic no disponible: %s", exc)

    return printers


def _send_windows_printer(printer_name, command):
    """Envía 'command' (bytes) directamente a una impresora Windows.

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

    # Intento 2: copy /b <tmpfile> "\\.\<impresora>"  (RAW)
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


def _get_docker_gateway():
    """Devuelve la IP de la gateway del contenedor Docker (= host Linux).
    Permite consultar los servicios del host (p. ej. CUPS) desde dentro
    del contenedor sin necesidad de modificar docker-compose.yml.
    """
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
class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    cash_drawer_printer_select = fields.Selection(
        selection="_get_available_printers",
        string="Impresora del cajón portamonedas",
        help=(
            "Selecciona la impresora de la lista. "
            "Para impresoras de red puedes introducir directamente "
            "\u00abIP:puerto\u00bb (p. ej. 192.168.1.50:9100)."
        ),
    )
    # Campo editable: persiste la elección en ir.config_parameter
    cash_drawer_printer_path = fields.Char(
        string="Impresora configurada",
        config_parameter="cash_drawer_settings.printer_path",
        help=(
            "Dirección de la impresora. "
            "Red: IP:puerto (p. ej. 192.168.1.50:9100). "
            "CUPS: nombre de la cola."
        ),
    )

    cash_drawer_command_bytes = fields.Char(
        string="Comando de apertura (bytes)",
        config_parameter="cash_drawer_settings.command_bytes",
        help=(
            "Bytes del comando ESC/POS que abre el cajón, en decimal separados "
            "por espacios. Ejemplos:\n"
            "  27 112 0 25 250  → ESC p (estándar)\n"
            "  27 105           → ESC i\n"
            "  27 112 1 25 250  → ESC p pin 5"
        ),
    )
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_available_printers(self):
        """Devuelve la lista de impresoras/dispositivos disponibles en el sistema.

        - Windows: consulta las impresoras instaladas via PowerShell / wmic.
        - Linux:   busca ficheros de dispositivo (/dev/…) y colas CUPS locales
                   y del host Docker (lpstat -h <gateway>).
        En ambos casos incluye el valor guardado si no está ya en la lista.
        """
        printers = []

        if _IS_WINDOWS:
            # --- Detección en Windows ---
            printers = _detect_windows_printers()
        else:
            # --- Detección en Linux ---
            # 1. Ficheros de dispositivo locales
            for pattern in _DEVICE_PATTERNS:
                for dev in sorted(glob.glob(pattern)):
                    if dev not in [p[0] for p in printers]:
                        printers.append((dev, dev))
            # 2. Colas CUPS locales
            printers = self._lpstat_to_list(printers, host=None)
            # 3. Colas CUPS del host (gateway Docker)
            gateway = _get_docker_gateway()
            if gateway:
                printers = self._lpstat_to_list(printers, host=gateway)

        # Valor guardado: incluirlo siempre para evitar errores de validación
        stored = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.printer_path", "")
        )
        if stored and stored not in [p[0] for p in printers]:
            printers.insert(0, (stored, u"%s (\u2605 guardado)" % stored))

        return printers

    @api.model
    def _lpstat_to_list(self, printers, host=None):
        """Ejecuta lpstat -a (opcionalmente contra un host remoto) y añade
        las colas encontradas a la lista, evitando duplicados."""
        cmd = ["lpstat", "-a"]
        label_suffix = " (CUPS)"
        if host:
            cmd += ["-h", host]
            label_suffix = u" (CUPS en %s)" % host
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=3, text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if parts:
                        name = parts[0].strip()
                        if name and name not in [p[0] for p in printers]:
                            printers.append(
                                (name, u"🖨 %s%s" % (name, label_suffix))
                            )
        except Exception as exc:
            _logger.debug("lpstat%s no disponible: %s",
                          (" -h " + host) if host else "", exc)
        return printers

    @api.onchange("cash_drawer_printer_select")
    def _onchange_cash_drawer_printer_select(self):
        """Copia la impresora seleccionada al campo de almacenamiento."""
        self.cash_drawer_printer_path = self.cash_drawer_printer_select or False

    def get_values(self):
        """Preselecciona el desplegable con el valor guardado al abrir Ajustes."""
        res = super().get_values()
        stored = res.get("cash_drawer_printer_path") or (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.printer_path", "")
        )
        if stored:
            res["cash_drawer_printer_select"] = stored
        return res
    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_detect_printers(self):
        """Detecta impresoras USB/serie/CUPS y muestra un diálogo con los resultados.

        No modifica ninguna configuración, solo escanea y muestra información.
        """
        self.ensure_one()

        detected = []

        if _IS_WINDOWS:
            # Windows: PowerShell + wmic
            detected = _detect_windows_printers()
            if not detected:
                detected.append(
                    ("", "⚠️ No se detectaron impresoras Windows. Verifica que estén instaladas en 'Dispositivos e impresoras'.")
                )
        else:
            # Linux: dispositivos /dev/
            for pattern in _DEVICE_PATTERNS:
                for dev in sorted(glob.glob(pattern)):
                    # Verificar si el dispositivo existe y es accesible
                    try:
                        if os.path.exists(dev) and not os.path.isdir(dev):
                            # Intentar determinar si es escribible
                            writable = os.access(dev, os.W_OK)
                            status = "✅" if writable else "🔒 (sin permisos)"
                            detected.append((dev, f"{status} {dev}"))
                    except Exception:
                        pass

            # CUPS local
            try:
                result = subprocess.run(
                    ["lpstat", "-a"], capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = line.split()
                        if parts:
                            detected.append((parts[0], f"🖨 {parts[0]} (CUPS local)"))
            except Exception:
                pass

            # CUPS del host (gateway Docker)
            gateway = _get_docker_gateway()
            if gateway:
                try:
                    result = subprocess.run(
                        ["lpstat", "-h", gateway, "-a"],
                        capture_output=True, text=True, timeout=3
                    )
                    if result.returncode == 0:
                        for line in result.stdout.splitlines():
                            parts = line.split()
                            if parts:
                                detected.append(
                                    (parts[0], f"🖨 {parts[0]} (CUPS en {gateway})")
                                )
                except Exception:
                    pass

        # Construir mensaje
        if detected:
            msg_lines = ["<b>Impresoras y dispositivos detectados:</b><br/><br/>"]
            for path, label in detected:
                msg_lines.append(f"• {label}<br/>")
            msg_lines.append("<br/><b>Para usar una:</b><br/>")
            msg_lines.append("1. Copia el nombre/ruta exacto<br/>")
            msg_lines.append("2. Pégalo en el campo 'Impresora configurada'<br/>")
            msg_lines.append("3. Guarda y prueba con el botón 'Abrir cajón'")
            message = "".join(msg_lines)
            title = f"✅ {len(detected)} impresora(s) encontrada(s)"
        else:
            message = (
                "<b>No se detectaron impresoras USB/serie.</b><br/><br/>"
                "Posibles causas:<br/>"
                "• La impresora no está conectada<br/>"
                "• Faltan permisos (prueba como root)<br/>"
                "• Es una impresora de red → usa IP:puerto directamente<br/><br/>"
                "<b>Impresora de red:</b><br/>"
                "Escribe directamente en 'Impresora configurada':<br/>"
                "192.168.X.X:9100"
            )
            title = "⚠️ Sin impresoras detectadas"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "info" if detected else "warning",
                "sticky": True,
            },
        }

    def action_open_cash_drawer(self):
        """Envía el comando ESC/POS de apertura de cajón (bytes 27, 105).
        Intentos en orden:
        1. Socket TCP directo  — cuando la ruta tiene formato  host:puerto.
        2. lpr contra el host  — cola CUPS del host Linux (via gateway Docker).
        3. lpr local           — cola CUPS local del contenedor.
        4. Escritura directa   — fichero de dispositivo (/dev/...).
        """
        self.ensure_one()
        printer_path = (
            self.cash_drawer_printer_path
            or self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.printer_path", "")
        ).strip()
        if not printer_path:
            raise UserError(
                _("No hay ninguna impresora configurada. "
                  "Seléccion una en Ajustes \u2192 Cajón Portamonedas.")
            )

        # Obtener y parsear los bytes del comando
        raw_bytes = (
            self.cash_drawer_command_bytes
            or self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.command_bytes", "")
        ).strip()

        if raw_bytes:
            try:
                command = bytes(
                    int(b) for b in raw_bytes.split() if b.strip()
                )
                if not command:
                    raise ValueError("vacío")
            except (ValueError, TypeError) as exc:
                raise UserError(
                    _("El comando de apertura no es válido: %r\n"
                      "Introduce bytes decimales separados por espacios "
                      "(p. ej. 27 112 0 25 250).") % raw_bytes
                ) from exc
        else:
            command = _CASH_DRAWER_COMMAND
        _logger.info(
            "Intentando abrir cajón portamonedas. Destino: %s", printer_path
        )
        errors = []
        tcp_match = _TCP_RE.match(printer_path)

        # --- Intento 0: impresora Windows (solo en servidor Windows) ---
        if _IS_WINDOWS and not tcp_match:
            try:
                _send_windows_printer(printer_path, command)
                _logger.info("Cajón abierto via impresora Windows: %s", printer_path)
                return self._cash_drawer_ok_notification()
            except Exception as exc:
                _logger.warning("Windows printer %s falló: %s", printer_path, exc)
                errors.append(_("Windows %s: %s") % (printer_path, exc))

        # --- Intento 1: socket TCP directo (formato IP:puerto) ---
        if tcp_match:
            host, port = tcp_match.group(1), int(tcp_match.group(2))
            try:
                with socket.create_connection((host, port), timeout=5) as sock:
                    sock.sendall(command)
                _logger.info(
                    "Cajón abierto correctamente via TCP %s:%s", host, port
                )
                return self._cash_drawer_ok_notification()
            except OSError as exc:
                _logger.warning("TCP %s:%s falló: %s", host, port, exc)
                errors.append(_("TCP %s:%s → %s") % (host, port, exc))
        # Preparar fichero temporal con el comando para los intentos lpr
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                tmp.write(command)
                tmp_path = tmp.name
            # --- Intento 2: lpr contra el host (gateway Docker) ---
            if not tcp_match:
                gateway = _get_docker_gateway()
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
                            return self._cash_drawer_ok_notification()
                        stderr = result.stderr.decode(errors="replace").strip()
                        errors.append(
                            _("lpr -h %s -P %s: %s") % (
                                gateway, printer_path, stderr or result.returncode
                            )
                        )
                    except FileNotFoundError:
                        errors.append(_("Comando lpr no encontrado en el sistema."))
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
                        return self._cash_drawer_ok_notification()
                    stderr = result.stderr.decode(errors="replace").strip()
                    errors.append(
                        _("lpr -P %s: %s") % (printer_path, stderr or result.returncode)
                    )
                except FileNotFoundError:
                    pass  # ya añadido en intento 2
                except subprocess.TimeoutExpired:
                    errors.append(_("Tiempo de espera agotado (lpr)."))
                except Exception as exc:
                    errors.append(str(exc))
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        # --- Intento 4: escritura directa al fichero de dispositivo ---
        if not tcp_match and os.path.exists(printer_path) and not os.path.isdir(printer_path):
            try:
                with open(printer_path, "wb") as dev:
                    dev.write(command)
                _logger.info(
                    "Cajón abierto via dispositivo: %s", printer_path
                )
                return self._cash_drawer_ok_notification()
            except OSError as exc:
                errors.append(_("Dispositivo %s: %s") % (printer_path, exc))
        # --- Todos los intentos fallaron ---
        raise UserError(
            _(
                "No se pudo abrir el cajón portamonedas.\n"
                "Destino configurado: %(path)s\n\n"
                "Errores:\n%(errors)s"
            )
            % {
                "path": printer_path,
                "errors": "\n".join(errors) or _("Error desconocido"),
            }
        )

    def _cash_drawer_ok_notification(self):
        """Devuelve una acción de notificación de éxito para mostrar en cliente."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cajón portamonedas"),
                "message": _("Comando de apertura enviado correctamente."),
                "type": "success",
                "sticky": False,
            },
        }
