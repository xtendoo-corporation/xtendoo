# Copyright 2023 Jaime Millan (<https://xtendoo.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    # def can_be_valid_dow(self, date_ref, contract):
    #     dow = date_ref.strftime("%A")
    #     if dow=='Monday' and contract.monday:
    #         return True
    #     if dow == 'Tuesday' and contract.tuesday:
    #         return True
    #     if dow == 'Wednesday' and contract.wednesday:
    #         return True
    #     if dow == 'Thursday' and contract.thursday:
    #         return True
    #     if dow == 'Friday' and contract.friday:
    #         return True
    #     if dow == 'Saturday' and contract.saturday:
    #         return True
    #     if dow == 'Sunday' and contract.sunday:
    #         return True

    def can_be_valid_dow(self, date_ref, contract):
        dow = date_ref.strftime("%A")
        return (
            (dow == 'Monday' and contract.monday) or
            (dow == 'Tuesday' and contract.tuesday) or
            (dow == 'Wednesday' and contract.wednesday) or
            (dow == 'Thursday' and contract.thursday) or
            (dow == 'Friday' and contract.friday) or
            (dow == 'Saturday' and contract.saturday) or
            (dow == 'Sunday' and contract.sunday)
        )

    def _prepare_recurring_sales_values(self, date_ref=False):
        """
        This method builds the list of sales values to create, based on
        the lines to sale of the contracts in self.
        !!! The date of next invoice (recurring_next_date) is updated here !!!
        :return: list of dictionaries (invoices values)
        """

        print("*"*80)
        print("_prepare_recurring_sales_values")
        print("date_ref", date_ref)
        print("*"*80)

        sales_values = []

        for contract in self:

            print("*" * 80)
            print("contract", contract)
            print("*" * 80)

            if not date_ref:
                date_ref = contract.recurring_next_date

            print("*" * 80)
            print("date_ref", date_ref)
            print("date_ref.strftime(%A)",date_ref.strftime("%A"))
            print("recurring_rule_type",contract.recurring_rule_type)
            print("*" * 80)

            if contract.recurring_rule_type=='daily':
                if not self.can_be_valid_dow(date_ref, contract):
                    contract.contract_line_ids.mapped(lambda l: l._update_recurring_next_date())

            if not date_ref:
                # this use case is possible when recurring_create_invoice is
                # called for a finished contract
                continue
            contract_lines = contract._get_lines_to_invoice(date_ref)
            if not contract_lines:
                continue
            sale_values = contract._prepare_sale(date_ref)
            for line in contract_lines:
                sale_values.setdefault("order_line", [])
                invoice_line_values = line._prepare_sale_line(
                    sale_values=sale_values,
                )
                if invoice_line_values:
                    sale_values["order_line"].append((0, 0, invoice_line_values))
            sales_values.append(sale_values)
            contract_lines._update_recurring_next_date()
        return sales_values

