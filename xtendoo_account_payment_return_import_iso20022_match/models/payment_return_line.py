# Copyright 2026 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PaymentReturnLine(models.Model):
    _inherit = "payment.return.line"

    def _resolve_partner_from_name(self):
        """Resolve partner_id from partner_name using exact name match.

        Only assigns partner_id if exactly one customer is found with that
        name. Logs a warning and leaves partner_id empty when zero or multiple
        matches are found.
        """
        for line in self.filtered(lambda x: not x.partner_id and x.partner_name):
            partners = self.env["res.partner"].search(
                [
                    ("name", "=", line.partner_name),
                    ("customer_rank", ">", 0),
                ]
            )
            if len(partners) == 1:
                line.partner_id = partners
            elif len(partners) == 0:
                _logger.warning(
                    "No customer found with exact name '%s' for payment return "
                    "line %s. Partner will not be assigned automatically.",
                    line.partner_name,
                    line.id,
                )
            else:
                _logger.warning(
                    "Multiple customers found (%d) with name '%s' for payment "
                    "return line %s. Partner will not be assigned automatically.",
                    len(partners),
                    line.partner_name,
                    line.id,
                )

    def match_invoice_by_concept(self):
        """Match move_line_ids using the concept field as invoice reference.

        The concept field contains the RmtInf/Ustrd value from ISO20022 PAIN
        002 files, which typically holds the original invoice name
        (e.g. 'HERM/2026/00536'). This method searches for an out_invoice
        with that name and extracts its reconciled payment lines.
        """
        for line in self.filtered(lambda x: not x.move_line_ids and x.concept):
            domain = []
            if line.partner_id:
                domain.append(("partner_id", "=", line.partner_id.id))
            domain += [
                ("name", "=", line.concept),
                ("move_type", "=", "out_invoice"),
            ]
            invoice = self.env["account.move"].search(domain, limit=1)
            if not invoice:
                continue
            receivable_lines = invoice.line_ids.filtered(
                lambda aml: aml.account_id.account_type == "asset_receivable"
            )
            payment_lines = receivable_lines.mapped("matched_debit_ids.debit_move_id")
            payment_lines |= receivable_lines.mapped(
                "matched_credit_ids.credit_move_id"
            )
            if payment_lines:
                line.move_line_ids = payment_lines[-1].ids

    def match_move_lines_by_concept(self):
        """Fallback: match move_line_ids using concept as move line reference.

        Searches account.move.line with account_type = asset_receivable,
        reconciled = True and name or ref equal to the concept value. Useful
        when the payment was registered without a direct invoice link.
        """
        for line in self.filtered(lambda x: not x.move_line_ids and x.concept):
            domain = []
            if line.partner_id:
                domain.append(("partner_id", "=", line.partner_id.id))
            if line.return_id.journal_id:
                domain += [
                    ("credit", ">", 0.0),
                    ("move_id.move_type", "=", "entry"),
                ]
            domain += [
                ("account_id.account_type", "=", "asset_receivable"),
                ("reconciled", "=", True),
                "|",
                ("name", "=", line.concept),
                ("ref", "=", line.concept),
            ]
            move_lines = self.env["account.move.line"].search(domain)
            if move_lines:
                line.move_line_ids = move_lines.ids

    def _find_match(self):
        """Extend standard matching with concept-based and partner-name strategies.

        Execution order:
        1. super() runs the standard matching pipeline (payment order ID,
           invoice by reference, move lines by reference, move by reference).
        2. For lines still unmatched, resolve partner_id from partner_name
           (exact match only).
        3. Try to match move_line_ids using concept as invoice name.
        4. Fallback: try to match move_line_ids using concept as move line ref.
        """
        super()._find_match()

        unmatched = self.filtered(lambda x: not x.move_line_ids)
        if not unmatched:
            return

        unmatched._resolve_partner_from_name()

        unmatched.match_invoice_by_concept()

        unmatched = unmatched.filtered(lambda x: not x.move_line_ids)
        unmatched.match_move_lines_by_concept()

