# -*- coding: utf-8 -*-
"""Extensión de pos.config para integrar el cajón portamonedas en el TPV."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import cash_drawer_utils


class PosConfig(models.Model):
    _inherit = "pos.config"

    # ------------------------------------------------------------------
    # Campos
    # ------------------------------------------------------------------

    cash_drawer_pos_enabled = fields.Boolean(
        string="Botón de cajón en TPV",
        default=False,
        help=(
            "Muestra un botón en el menú del TPV para abrir el cajón "
            "portamonedas directamente desde la interfaz del punto de venta."
        ),
    )

    # ------------------------------------------------------------------
    # Métodos RPC llamados desde el TPV (JavaScript)
    # ------------------------------------------------------------------

    def action_pos_open_cash_drawer(self):
        """Abre el cajón portamonedas desde el TPV via RPC.

        Utiliza la configuración global de ``ir.config_parameter``:
          * ``cash_drawer_settings.printer_path``
          * ``cash_drawer_settings.command_bytes``

        Se usa como último recurso (fallback) cuando las estrategias
        del lado del navegador (HW Proxy, WebUSB, proxy local) fallan.

        Returns:
            dict: Notificación de éxito (ir.actions.client)

        Raises:
            UserError: si no hay impresora configurada o todos los
                       intentos de apertura fracasan.
        """
        self.ensure_one()

        ICP = self.env["ir.config_parameter"].sudo()
        printer_path = ICP.get_param(
            "cash_drawer_settings.printer_path", ""
        ).strip()
        command_bytes_str = ICP.get_param(
            "cash_drawer_settings.command_bytes", ""
        ).strip()

        if not printer_path:
            raise UserError(
                _(
                    "No hay ninguna impresora configurada para el cajón "
                    "portamonedas.\n\n"
                    "Configúrala en Ajustes → Cajón Portamonedas."
                )
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

