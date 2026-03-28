# -*- coding: utf-8 -*-
"""Ajustes globales del cajón portamonedas en res.config.settings."""
import glob
import logging
import subprocess

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import cash_drawer_utils

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    # Campos
    # ------------------------------------------------------------------

    cash_drawer_printer_select = fields.Selection(
        selection="_get_available_printers",
        string="Impresora del cajón portamonedas",
        help=(
            "Selecciona la impresora de la lista. "
            "Para impresoras de red puedes introducir directamente "
            "\u00abIP:puerto\u00bb (p. ej. 192.168.1.50:9100)."
        ),
    )

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
    # Helpers de detección
    # ------------------------------------------------------------------

    @api.model
    def _get_available_printers(self):
        """Devuelve la lista de impresoras/dispositivos disponibles en el sistema."""
        printers = []

        if cash_drawer_utils._IS_WINDOWS:
            printers = cash_drawer_utils.detect_windows_printers()
        else:
            # Ficheros de dispositivo locales
            for pattern in cash_drawer_utils.DEVICE_PATTERNS:
                for dev in sorted(glob.glob(pattern)):
                    if dev not in [p[0] for p in printers]:
                        printers.append((dev, dev))
            # Colas CUPS locales
            printers = self._lpstat_to_list(printers, host=None)
            # Colas CUPS del host (gateway Docker)
            gateway = cash_drawer_utils.get_docker_gateway()
            if gateway:
                printers = self._lpstat_to_list(printers, host=gateway)

        # Valor guardado: incluirlo siempre para evitar errores de validación
        stored = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.printer_path", "")
        )
        if stored and stored not in [p[0] for p in printers]:
            printers.insert(0, (stored, "%s (\u2605 guardado)" % stored))

        return printers

    @api.model
    def _lpstat_to_list(self, printers, host=None):
        """Ejecuta lpstat -a y añade las colas encontradas a la lista."""
        cmd = ["lpstat", "-a"]
        label_suffix = " (CUPS)"
        if host:
            cmd += ["-h", host]
            label_suffix = " (CUPS en %s)" % host
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
                                (name, "\U0001f5a8 %s%s" % (name, label_suffix))
                            )
        except Exception as exc:
            _logger.debug(
                "lpstat%s no disponible: %s",
                (" -h " + host) if host else "",
                exc,
            )
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
        """Detecta impresoras USB/serie/CUPS y muestra un diálogo."""
        self.ensure_one()
        detected = []

        if cash_drawer_utils._IS_WINDOWS:
            detected = cash_drawer_utils.detect_windows_printers()
            if not detected:
                detected.append((
                    "",
                    "⚠️ No se detectaron impresoras Windows. "
                    "Verifica que estén instaladas en 'Dispositivos e impresoras'.",
                ))
        else:
            import os
            for pattern in cash_drawer_utils.DEVICE_PATTERNS:
                for dev in sorted(glob.glob(pattern)):
                    try:
                        if os.path.exists(dev) and not os.path.isdir(dev):
                            writable = os.access(dev, os.W_OK)
                            status = "✅" if writable else "🔒 (sin permisos)"
                            detected.append((dev, "%s %s" % (status, dev)))
                    except Exception:
                        pass

            try:
                result = subprocess.run(
                    ["lpstat", "-a"], capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = line.split()
                        if parts:
                            detected.append(
                                (parts[0], "\U0001f5a8 %s (CUPS local)" % parts[0])
                            )
            except Exception:
                pass

            gateway = cash_drawer_utils.get_docker_gateway()
            if gateway:
                try:
                    result = subprocess.run(
                        ["lpstat", "-h", gateway, "-a"],
                        capture_output=True, text=True, timeout=3,
                    )
                    if result.returncode == 0:
                        for line in result.stdout.splitlines():
                            parts = line.split()
                            if parts:
                                detected.append((
                                    parts[0],
                                    "\U0001f5a8 %s (CUPS en %s)" % (parts[0], gateway),
                                ))
                except Exception:
                    pass

        if detected:
            msg_lines = [
                "<b>Impresoras y dispositivos detectados:</b><br/><br/>"
            ]
            for _path, label in detected:
                msg_lines.append("• %s<br/>" % label)
            msg_lines += [
                "<br/><b>Para usar una:</b><br/>",
                "1. Copia el nombre/ruta exacto<br/>",
                "2. Pégalo en el campo 'Impresora configurada'<br/>",
                "3. Guarda y prueba con el botón 'Abrir cajón'",
            ]
            message = "".join(msg_lines)
            title = "✅ %d impresora(s) encontrada(s)" % len(detected)
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
        """Envía el comando ESC/POS de apertura de cajón desde Ajustes."""
        self.ensure_one()
        printer_path = (
            self.cash_drawer_printer_path
            or self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.printer_path", "")
        ).strip()

        if not printer_path:
            raise UserError(
                _(
                    "No hay ninguna impresora configurada. "
                    "Seléccionala en Ajustes \u2192 Cajón Portamonedas."
                )
            )

        command_bytes_str = (
            self.cash_drawer_command_bytes
            or self.env["ir.config_parameter"]
            .sudo()
            .get_param("cash_drawer_settings.command_bytes", "")
        ).strip()

        _logger.info(
            "Intentando abrir cajón portamonedas. Destino: %s", printer_path
        )

        try:
            cash_drawer_utils.open_cash_drawer(printer_path, command_bytes_str)
        except RuntimeError as exc:
            raise UserError(str(exc)) from exc

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
