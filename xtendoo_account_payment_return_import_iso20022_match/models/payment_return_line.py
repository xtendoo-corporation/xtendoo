# Copyright 2026 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class PaymentReturnLine(models.Model):
    _inherit = "payment.return.line"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger automatic matching after insert."""
        records = super().create(vals_list)
        # Only call _find_match if we're not already inside a matching operation
        # to prevent infinite recursion when _find_match triggers field assignments
        if not self.env.context.get("_payment_return_line_finding_match"):
            records = records.with_context(_payment_return_line_finding_match=True)
            records._find_match()
        return records

    def write(self, vals):
        """Override write to trigger automatic matching after update."""
        result = super().write(vals)
        # Only call _find_match if we're not already inside a matching operation
        if not self.env.context.get("_payment_return_line_finding_match"):
            self_context = self.with_context(_payment_return_line_finding_match=True)
            self_context._find_match()
        return result

    def _resolve_partner_from_name(self):
        """Resolve partner_id from partner_name using exact name match.

        Only assigns partner_id if exactly one customer is found with that
        name. Logs a warning and leaves partner_id empty when zero or multiple
        matches are found.
        """

        print("[PRL DEBUG] _resolve_partner_from_name - start line_ids=%s" % self.ids)

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

            # Assign partner from the found invoice
            if not line.partner_id and invoice.partner_id:
                line.partner_id = invoice.partner_id


            receivable_lines = invoice.line_ids.filtered(
                lambda aml: aml.account_id.account_type == "asset_receivable"
            )
            payment_lines = receivable_lines.mapped("matched_debit_ids.debit_move_id")
            payment_lines |= receivable_lines.mapped("matched_credit_ids.credit_move_id")


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
        2. Resolve partner_id from partner_name for all lines (exact match only).
        3. For lines still unmatched, try to match move_line_ids using concept
           as invoice name.
        4. Fallback: for unmatched lines, try to match move_line_ids using
           concept as move line ref.
        """
        super()._find_match()

        # Always attempt partner resolution for every line.
        self._resolve_partner_from_name()

        unmatched = self.filtered(lambda x: not x.move_line_ids)

        if not unmatched:
            return

        unmatched.match_invoice_by_concept()

        unmatched = unmatched.filtered(lambda x: not x.move_line_ids)

        unmatched.match_move_lines_by_concept()

