from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_main_bank_account(self):
        """
        Obtiene la cuenta principal del diario de banco.
        Prioridad:
        1. default_account_id si existe y es de tipo liquidez (asset_cash)
        2. payment_debit_account_id
        3. payment_credit_account_id
        """
        self.ensure_one()
        if self.default_account_id and self.default_account_id.account_type == "asset_cash":
            return self.default_account_id
        if self.payment_debit_account_id:
            return self.payment_debit_account_id
        if self.payment_credit_account_id:
            return self.payment_credit_account_id
        return self.env["account.account"]

    def _get_subaccounts(self, main_account):
        """
        Obtiene todas las subcuentas (cuentas descendientes) de la cuenta principal.
        Las subcuentas son aquellas cuentas cuyo código comienza con el código
        de la cuenta principal, excluyendo la cuenta principal misma.
        """
        if not main_account or not main_account.code:
            return self.env["account.account"]

        # Buscar cuentas cuyo código comience con el código de la cuenta principal
        # y que pertenezcan a la misma compañía, excluyendo la cuenta principal
        domain = [
            ("code", "=like", main_account.code + "%"),
            ("id", "!=", main_account.id),
            ("company_ids", "in", self.company_id.ids),
        ]
        return self.env["account.account"].search(domain)

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        """Extiende el método para añadir el saldo de subcuentas."""
        super()._fill_bank_cash_dashboard_data(dashboard_data)

        # Solo procesar diarios de tipo banco
        bank_journals = self.filtered(lambda j: j.type == "bank")
        if not bank_journals:
            return

        # Recopilar información de subcuentas por diario
        journal_subaccounts = {}
        all_subaccount_ids = []

        for journal in bank_journals:
            main_account = journal._get_main_bank_account()
            if main_account:
                subaccounts = journal._get_subaccounts(main_account)
                if subaccounts:
                    journal_subaccounts[journal.id] = {
                        "main_account": main_account,
                        "subaccounts": subaccounts,
                        "company_id": journal.company_id.id,
                    }
                    all_subaccount_ids.extend(subaccounts.ids)

        if not all_subaccount_ids:
            # No hay subcuentas, inicializar datos vacíos
            for journal in bank_journals:
                dashboard_data[journal.id].update({
                    "subaccounts_balance": False,
                    "has_subaccounts": False,
                })
            return

        # Calcular saldos de forma eficiente con read_group
        # Agrupar por cuenta y obtener la suma del balance
        balances = self.env["account.move.line"].read_group(
            [
                ("account_id", "in", list(set(all_subaccount_ids))),
                ("parent_state", "=", "posted"),
            ],
            ["balance:sum"],
            ["account_id", "company_id"],
            lazy=False,
        )

        # Crear mapa de balances: {(account_id, company_id): balance}
        balance_map = {}
        for b in balances:
            key = (b["account_id"][0], b["company_id"][0])
            balance_map[key] = b["balance"]

        # Calcular el saldo total de subcuentas por diario
        for journal in bank_journals:
            journal_data = journal_subaccounts.get(journal.id)

            if not journal_data:
                dashboard_data[journal.id].update({
                    "subaccounts_balance": False,
                    "has_subaccounts": False,
                })
                continue

            subaccounts = journal_data["subaccounts"]
            company_id = journal_data["company_id"]

            # Sumar el balance de todas las subcuentas para esta compañía
            total_balance = sum(
                balance_map.get((acc.id, company_id), 0.0)
                for acc in subaccounts
            )

            # Formatear el saldo con la moneda correcta
            currency = (
                journal.currency_id or journal.company_id.sudo().currency_id
            ).with_env(self.env)

            dashboard_data[journal.id].update({
                "subaccounts_balance": currency.format(total_balance),
                "subaccounts_balance_raw": total_balance,
                "has_subaccounts": bool(subaccounts),
                "subaccounts_count": len(subaccounts),
            })
