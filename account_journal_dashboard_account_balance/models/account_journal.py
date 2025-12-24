from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        # Incluimos 'credit' y aseguramos que el tipo sea capturado correctamente
        bank_cash_journals = self.filtered(
            lambda j: j.type in ["bank", "cash", "credit"] and j.default_account_id
        )
        if not bank_cash_journals:
            return

        account_ids = bank_cash_journals.mapped("default_account_id").ids
        company_ids = bank_cash_journals.mapped("company_id").ids

        # Calcular saldos de forma eficiente con read_group
        balances = self.env["account.move.line"].read_group(
            [
                ("account_id", "in", account_ids),
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
            ],
            ["balance", "account_id"],
            ["account_id"],
        )
        balance_map = {b["account_id"][0]: b["balance"] for b in balances}

        for journal in bank_cash_journals:
            currency = (
                journal.currency_id or journal.company_id.sudo().currency_id
            ).with_env(self.env)
            account_balance = balance_map.get(journal.default_account_id.id, 0.0)

            dashboard_data[journal.id].update(
                {
                    "account_id_balance": currency.format(account_balance),
                    "account_id_name": journal.default_account_id.display_name,
                }
            )
