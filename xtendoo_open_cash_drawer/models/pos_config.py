# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError

from .cash_drawer_utils import open_cash_drawer


class PosConfig(models.Model):
    _inherit = "pos.config"

    # ---------------------------------------------------------------
    # Direct ESC/POS strategy (no print job needed)
    # ---------------------------------------------------------------
    cash_drawer_printer_address = fields.Char(
        string="Cash Drawer Printer Address",
        help=(
            "Address of the printer connected to the cash drawer.\n\n"
            "Formats accepted:\n"
            "• Network printer:  192.168.1.50:9100\n"
            "• CUPS printer:     EPSON_TM_T20\n"
            "• USB device (Linux): /dev/usb/lp0\n"
            "• Docker host printer: host:9100  "
            "(automatically resolves to the Docker bridge gateway)\n\n"
            "When set, the 'Open Drawer' button sends the ESC/POS command "
            "directly to the printer WITHOUT printing any receipt.\n"
            "Leave empty to rely on the POS printer service / dummy print fallback."
        ),
    )
    cash_drawer_command_bytes = fields.Char(
        string="ESC/POS Command Bytes",
        default="27 112 0 25 250",
        help=(
            "Space-separated decimal byte values for the ESC/POS cash drawer "
            "open command sent directly to the printer.\n\n"
            "Common values:\n"
            "• 27 112 0 25 250  — ESC p, pin 2 (most ESC/POS printers)\n"
            "• 27 112 1 25 250  — ESC p, pin 5\n"
            "• 7                — BEL (some Star Micronics models)\n\n"
            "Leave empty to use the default (27 112 0 25 250)."
        ),
    )

    # ---------------------------------------------------------------
    # Dummy-print fallback strategy
    # ---------------------------------------------------------------
    cash_drawer_dummy_print = fields.Boolean(
        string="Open Cash Drawer via Dummy Print (fallback)",
        default=False,
        help=(
            "Enables the 'Open Cash Drawer' button in the POS burger menu.\n\n"
            "When pressed, a minimal (dummy) receipt will be sent to the configured "
            "POS printer. If your printer is set up to open the cash drawer when "
            "printing, the drawer will open automatically.\n\n"
            "This is used as a LAST RESORT fallback when the direct ESC/POS strategy "
            "('Cash Drawer Printer Address') is not configured and the POS printer "
            "service does not expose an openCashbox() method.\n\n"
            "IMPORTANT: This option sends a minimal print job to the printer. "
            "No real order, payment or commercial receipt is created."
        ),
    )
    cash_drawer_dummy_text = fields.Char(
        string="Dummy Print Text",
        default=".",
        help="Minimal text sent in the dummy receipt used to trigger drawer opening.",
    )
    cash_drawer_web_print_fallback = fields.Boolean(
        string="Use Web Print as Fallback",
        default=False,
        help=(
            "If the hardware proxy / direct ESC/POS command is unavailable, "
            "fall back to the browser's Web Print API to trigger the receipt print."
        ),
    )

    # ---------------------------------------------------------------
    # Server-side direct opening (called from the POS frontend)
    # ---------------------------------------------------------------

    def open_cash_drawer_direct(self):
        """Send the ESC/POS cash-drawer pulse directly to the configured printer.

        This method is called via JSON-RPC from the POS frontend.  It uses
        :func:`~.cash_drawer_utils.open_cash_drawer` to communicate with the
        printer over TCP or through a local device / CUPS, **without** sending
        any print job.

        :raises UserError: when no printer address is configured or the
                           connection fails.
        :returns: ``{"success": True}`` on success.
        """
        self.ensure_one()
        if not self.cash_drawer_printer_address:
            raise UserError(
                _(
                    "No printer address configured for direct cash drawer opening.\n"
                    "Set 'Cash Drawer Printer Address' in the POS configuration."
                )
            )
        try:
            open_cash_drawer(
                self.cash_drawer_printer_address,
                self.cash_drawer_command_bytes or None,
            )
            return {"success": True}
        except RuntimeError as exc:
            raise UserError(str(exc)) from exc
