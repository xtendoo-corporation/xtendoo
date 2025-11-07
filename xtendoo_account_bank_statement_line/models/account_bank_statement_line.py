# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # Añadimos campos computados para mostrar información adicional útil
    display_name_custom = fields.Char(
        string='Display Name',
        compute='_compute_display_name_custom',
        store=False
    )

    @api.depends('payment_ref', 'date', 'amount')
    def _compute_display_name_custom(self):
        for line in self:
            line.display_name_custom = f"{line.date} - {line.payment_ref or 'N/A'} - {line.amount}"



