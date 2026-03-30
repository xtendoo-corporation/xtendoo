# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

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
