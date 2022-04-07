# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0

from odoo import _, api, fields, models


class L10nEsVatBook(models.Model):
    _inherit = "l10n.es.vat.book"
    _description = "Spanish VAT book report"

    def _get_account_move_lines(self, taxes, account=None):
        return self.env["account.move.line"].search(
            self._account_move_line_domain(taxes, account=account),
            order="move_id ASC, tax_line_id ASC")
