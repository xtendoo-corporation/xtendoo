# Copyright 2026 Xtendoo - Manuel Calero
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_draft(self):
        res = super().button_draft()

        invoices = self.filtered(lambda m: m.move_type in (
            'out_invoice',
            'out_refund',
            'in_invoice',
            'in_refund',
        ))

        for move in invoices:
            # 🔥 ESTA ES LA CLAVE REAL
            if move.invoice_pdf_report_id:
                move.invoice_pdf_report_id.unlink()
                move.invoice_pdf_report_id = False

        return res
