# -*- coding: utf-8 -*-
"""
Extension de pos.config para la estrategia de apertura de cajón por impresión dummy.

FILOSOFÍA:
  La apertura del cajón NO la realiza Odoo directamente mediante comandos hardware.
  Se provoca enviando una impresión mínima (dummy) a la impresora de tickets del TPV.
  Si la impresora está configurada para abrir el cajón al imprimir, lo hará
  automáticamente como consecuencia natural de cualquier impresión.

  Todo el mecanismo real ocurre en el frontend (OWL/JS), que usa el servicio
  estándar de impresión del POS para enviar el ticket dummy.

  Este modelo solo almacena la configuración necesaria en pos.config.
"""
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    # -----------------------------------------------------------------------
    # Activar/desactivar la estrategia de impresión dummy
    # -----------------------------------------------------------------------
    cash_drawer_dummy_print = fields.Boolean(
        string="Open Cash Drawer via Dummy Print",
        default=False,
        help=(
            "Enables the 'Open Cash Drawer' button in the POS burger menu.\n\n"
            "When pressed, a minimal (dummy) receipt will be sent to the configured "
            "POS printer. If your printer is set up to open the cash drawer when "
            "printing, the drawer will open automatically.\n\n"
            "IMPORTANT: This option does NOT send a direct hardware command to the "
            "drawer. It only triggers a minimal print so the printer can open the "
            "connected cash drawer if the printer is configured to do so.\n\n"
            "No real order, payment or commercial receipt is created."
        ),
    )

    # -----------------------------------------------------------------------
    # Texto configurable del ticket dummy
    # -----------------------------------------------------------------------
    cash_drawer_dummy_text = fields.Char(
        string="Dummy Print Text",
        default=".",
        help=(
            "Text to include in the dummy receipt used to trigger drawer opening.\n\n"
            "Keep it minimal. Examples:\n"
            "  · '.'  → single dot (default, least intrusive)\n"
            "  · ' '  → single space\n"
            "  · 'OPEN DRAWER' → visible technical label\n\n"
            "Some printers ignore completely blank content and do not cut/feed, "
            "which may prevent the drawer from opening. A single character like '.' "
            "is the safest minimum."
        ),
    )

    # -----------------------------------------------------------------------
    # Fallback: usar ventana de impresión web si no hay impresora ESC/POS
    # -----------------------------------------------------------------------
    cash_drawer_web_print_fallback = fields.Boolean(
        string="Use Web Print as Fallback",
        default=False,
        help=(
            "If no ESC/POS printer is configured in the POS, fall back to the "
            "browser's native print dialog (window.print). This will open the "
            "browser print window instead of printing directly to the thermal printer.\n\n"
            "Enable only if you are using a receipt printer configured at the OS level "
            "and accessible via the browser print function."
        ),
    )

    @api.model
    def _load_pos_data_fields(self, config):
        """ Include custom fields in the data loaded by the POS """
        res = super()._load_pos_data_fields(config)
        # If res is empty, Odoo reads all fields by default. 
        # Only append if res is already a restricted list of fields.
        if res:
            res += [
                "cash_drawer_dummy_print",
                "cash_drawer_dummy_text",
                "cash_drawer_web_print_fallback",
            ]
        return res
